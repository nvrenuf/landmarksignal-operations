"""Windows execution serialization and issue-bound approval checks.

The named mutex is authoritative; current.lock is diagnostic metadata only.
This module does not install a Hermes hook or establish who may grant approval.
"""

import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import threading
import time
import uuid

try:
    import win32event
except ImportError:
    win32event = None

HAS_WIN32EVENT = os.name == "nt" and win32event is not None
GUARD_DIR = str(Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "hermes/kanban")
GUARD_STATE_DIR = str(Path(GUARD_DIR) / "state")
GUARD_MUTEX_NAME = "LandmarkSignalV1Mutex"
GUARD_LOCK_FILE = str(Path(GUARD_DIR) / "current.lock")
_owners = threading.local()


class ExecutionGuardError(Exception):
    pass


class LockHeldError(ExecutionGuardError):
    pass


class UnauthorizedError(ExecutionGuardError):
    pass


class MutexUnavailableError(ExecutionGuardError):
    pass


def _identifier(value):
    value = str(value)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("IDs must contain only letters, digits, underscores or hyphens")
    return value


def _atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".guard-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _thread_owners():
    if not hasattr(_owners, "names"):
        _owners.names = set()
    return _owners.names


class ExecutionGuard:
    def __init__(self, github_issue_id, task_id, *, state_dir=None,
                 mutex_name=GUARD_MUTEX_NAME, timeout=10.0):
        self.github_issue_id = _identifier(github_issue_id)
        self.task_id = _identifier(task_id)
        if not isinstance(mutex_name, str) or not mutex_name or "\x00" in mutex_name:
            raise ValueError("Invalid mutex name")
        timeout = float(timeout)
        if not math.isfinite(timeout) or not 0 <= timeout <= 3600:
            raise ValueError("Timeout must be between zero and 3600 seconds")
        self.mutex_name = mutex_name
        self.timeout = timeout
        self._lock_file = str(Path(state_dir or GUARD_DIR) / "current.lock")
        self._mutex = None
        self._acquired = False
        self._owner = None
        self._token = None
        self.abandoned = False
        self._transition = threading.Lock()

    def acquire(self):
        with self._transition:
            if self._acquired or self.mutex_name in _thread_owners():
                raise LockHeldError("Recursive acquisition is forbidden")
            if not HAS_WIN32EVENT:
                raise MutexUnavailableError("Native Windows and pywin32 are required")
            handle = None
            owned = False
            try:
                # CreateMutex also opens an existing mutex with wait/release rights.
                handle = win32event.CreateMutex(None, False, self.mutex_name)
                result = win32event.WaitForSingleObject(handle, int(self.timeout * 1000))
                if result == win32event.WAIT_TIMEOUT:
                    raise LockHeldError("Another task owns the execution mutex")
                if result not in (win32event.WAIT_OBJECT_0, win32event.WAIT_ABANDONED):
                    raise MutexUnavailableError("Unexpected mutex wait result: %s" % result)
                owned = True
                self._mutex = handle
                self._acquired = True
                self._owner = (os.getpid(), threading.current_thread())
                self._token = uuid.uuid4().hex
                self.abandoned = result == win32event.WAIT_ABANDONED
                _thread_owners().add(self.mutex_name)
                # No expiry can release a live mutex. Rebuild only this metadata.
                _atomic_json(self._lock_file, {
                    "token": self._token, "github_issue_id": self.github_issue_id,
                    "task_id": self.task_id, "pid": os.getpid(),
                    "thread": threading.get_ident(), "acquired_at": time.time(),
                    "recovered_abandoned_mutex": self.abandoned,
                })
                return True
            except BaseException as error:
                if owned:
                    # Setup failure must not strand native ownership.
                    try:
                        win32event.ReleaseMutex(handle)
                    except Exception as release_error:
                        raise ExecutionGuardError("Setup failed and mutex release failed") from release_error
                    self._acquired = False
                    self._owner = None
                    self._mutex = None
                    _thread_owners().discard(self.mutex_name)
                if handle is not None:
                    handle.Close()
                if isinstance(error, (ExecutionGuardError, KeyboardInterrupt, SystemExit)):
                    raise
                if not owned:
                    raise MutexUnavailableError("Cannot create/wait for mutex") from error
                raise ExecutionGuardError("Cannot write execution metadata") from error

    def release(self):
        with self._transition:
            if not self._acquired or self._owner != (os.getpid(), threading.current_thread()):
                return False
            metadata_error = None
            try:
                try:
                    with open(self._lock_file, encoding="utf-8") as stream:
                        data = json.load(stream)
                    if not isinstance(data, dict) or data.get("token") != self._token:
                        raise ExecutionGuardError("Execution metadata ownership mismatch")
                    # Delete while still owning the mutex, never after releasing it.
                    os.unlink(self._lock_file)
                except FileNotFoundError:
                    pass
            except Exception as error:
                metadata_error = error
            # On ReleaseMutex failure retain ownership state for diagnosis/retry.
            try:
                win32event.ReleaseMutex(self._mutex)
            except Exception as error:
                raise ExecutionGuardError("Native mutex release failed") from error
            handle = self._mutex
            self._acquired = False
            self._owner = None
            self._mutex = None
            _thread_owners().discard(self.mutex_name)
            handle.Close()
            if metadata_error:
                raise ExecutionGuardError("Mutex released but metadata cleanup failed") from metadata_error
            return True

    def execute(self, func):
        self.acquire()
        try:
            return func()
        finally:
            self.release()


class ChildAuth:
    """Approval records, not an identity or tamper-proof authorization system.

    approve() is for a human-controlled integration only. An agent with write
    access to these files can approve itself; deployment must prevent that.
    """
    def __init__(self, *, state_dir=None):
        self.approval_dir = str(Path(state_dir or GUARD_STATE_DIR) / "approvals")

    def _path(self, child_id):
        child_id = _identifier(child_id)
        return Path(self.approval_dir) / ("child_" + hashlib.sha256(child_id.encode()).hexdigest() + ".json")

    def _read(self, child_id, github_issue_id=None):
        child_id = _identifier(child_id)
        try:
            with self._path(child_id).open(encoding="utf-8") as stream:
                data = json.load(stream)
            if not isinstance(data, dict) or data.get("child_id") != child_id:
                raise UnauthorizedError("Invalid child identity")
            if github_issue_id is not None and data.get("github_issue_id") != _identifier(github_issue_id):
                raise UnauthorizedError("Issue ID mismatch")
            return data
        except (OSError, ValueError, TypeError) as error:
            raise UnauthorizedError("Missing or malformed child approval") from error

    def propose(self, child_id, github_issue_id):
        child_id, github_issue_id = _identifier(child_id), _identifier(github_issue_id)
        path = self._path(child_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Do not silently overwrite an existing approval or proposal.
        with path.open("x", encoding="utf-8") as stream:
            json.dump({"child_id": child_id, "github_issue_id": github_issue_id,
                       "status": "proposed", "approved": False}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        return True

    def approve(self, child_id, github_issue_id):
        data = self._read(child_id, github_issue_id)
        if data.get("status") != "proposed" or data.get("approved") is not False:
            raise UnauthorizedError("Expected an unapproved proposal")
        data.update(status="approved", approved=True, approved_at=time.time())
        _atomic_json(self._path(child_id), data)
        return True

    def is_approved(self, child_id):
        try:
            data = self._read(child_id)
            return data.get("approved") is True and data.get("status") == "approved"
        except UnauthorizedError:
            return False

    def verify(self, child_id, github_issue_id):
        data = self._read(child_id, github_issue_id)
        if data.get("approved") is not True or data.get("status") != "approved":
            raise UnauthorizedError("Child is not approved")
        return True

    def execute(self, child_id, github_issue_id, func, *, guard):
        """Run a synchronous child inside its parent's owned execution scope.

        This does not authorize detached/subagent dispatch. Such a launch needs
        a verified Hermes boundary with the lock held until its work finishes.
        """
        if (not guard._acquired or
                guard._owner != (os.getpid(), threading.current_thread()) or
                guard.github_issue_id != _identifier(github_issue_id)):
            raise UnauthorizedError("Child requires its issue-bound parent execution scope")
        self.verify(child_id, github_issue_id)
        return func()
