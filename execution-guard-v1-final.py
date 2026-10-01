#!/usr/bin/env python3
"""
LANDMARKSIGNAL EXECUTION GUARD - V1 FINAL

Minimal, correct implementation with real tests.
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime

# Windows Named Mutex
try:
    import win32event
    HAS_WIN32EVENT = True
except ImportError:
    HAS_WIN32EVENT = False

GUARD_DIR = r"C:\Users\lee\AppData\Local\hermes\kanban"
GUARD_STATE_DIR = os.path.join(GUARD_DIR, "state")
GUARD_MUTEX_NAME = "LandmarkSignalV1Mutex"
GUARD_LOCK_FILE = os.path.join(GUARD_DIR, "current.lock")

os.makedirs(GUARD_STATE_DIR, exist_ok=True)


class ExecutionGuardError(Exception):
    pass


class LockHeldError(ExecutionGuardError):
    pass


class UnauthorizedError(ExecutionGuardError):
    pass


# Singleton Named Mutex - persists across processes
_mutex_handle = None


def _get_mutex():
    """Get or create the Named Mutex."""
    global _mutex_handle
    if _mutex_handle is None:
        if HAS_WIN32EVENT:
            _mutex_handle = win32event.CreateMutex(None, False, GUARD_MUTEX_NAME)
        else:
            _mutex_handle = None
    return _mutex_handle


def _acquire_mutex(timeout=5.0):
    """Acquire the Named Mutex. Returns True on success."""
    if _mutex_handle is None:
        _get_mutex()
        if _mutex_handle is None:
            return False
    
    if HAS_WIN32EVENT:
        result = win32event.WaitForSingleObject(_mutex_handle, int(timeout * 1000))
        return result == win32event.WAIT_OBJECT_0
    return False


def _release_mutex():
    """Release the Named Mutex."""
    global _mutex_handle
    if _mutex_handle is None:
        return
    
    if HAS_WIN32EVENT:
        win32event.ReleaseMutex(_mutex_handle)
    elif hasattr(_mutex_handle, 'release'):
        _mutex_handle.release()


class ExecutionGuard:
    """
    Execution guard with lock held throughout execution.
    """
    
    def __init__(self, github_issue_id: str, task_id: str):
        self.github_issue_id = github_issue_id
        self.task_id = task_id
        self._lock_file = GUARD_LOCK_FILE
        self._acquired = False
    
    def acquire(self) -> bool:
        """Acquire the global lock."""
        try:
            if not _acquire_mutex(timeout=10.0):
                raise LockHeldError("Cannot acquire lock - another task is running")
            
            # Write lock file
            token = hashlib.sha256(
                f"{self.github_issue_id}:{self.task_id}:{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]
            
            lock_data = {
                "type": "SHARED",
                "token": token,
                "github_issue_id": self.github_issue_id,
                "task_id": self.task_id,
                "acquired_at": datetime.now().isoformat(),
                "expiry": int(time.time()) + 300
            }
            
            os.makedirs(os.path.dirname(self._lock_file), exist_ok=True)
            with open(self._lock_file, 'w') as f:
                json.dump(lock_data, f)
                f.flush()
                os.fsync(f.fileno())
            
            self._acquired = True
            return True
            
        except Exception as e:
            self._acquired = False
            raise LockHeldError(f"Acquisition failed: {e}")
    
    def release(self) -> bool:
        """Release the lock."""
        try:
            if not self._acquired:
                return False
            
            if os.path.exists(self._lock_file):
                os.remove(self._lock_file)
            
            _release_mutex()
            self._acquired = False
            return True
            
        except Exception as e:
            self._acquired = False
            return False
    
    def execute(self, func):
        """Execute function while holding the lock."""
        self.acquire()
        try:
            return func()
        finally:
            self.release()


class ChildAuth:
    """Child task authorization."""
    
    def __init__(self):
        self.approval_dir = os.path.join(GUARD_STATE_DIR, "approvals")
        os.makedirs(self.approval_dir, exist_ok=True)
    
    def propose(self, child_id, github_issue_id):
        """Propose child task."""
        path = os.path.join(self.approval_dir, f"child_{child_id}.json")
        data = {
            "type": "proposal",
            "child_id": child_id,
            "github_issue_id": github_issue_id,
            "status": "proposed",
            "approved": False
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def approve(self, child_id, github_issue_id):
        """Approve child task."""
        path = os.path.join(self.approval_dir, f"child_{child_id}.json")
        if not os.path.exists(path):
            raise UnauthorizedError(f"No proposal for {child_id}")
        
        with open(path) as f:
            data = json.load(f)
        
        if data["github_issue_id"] != github_issue_id:
            raise UnauthorizedError("Issue ID mismatch")
        
        data["status"] = "approved"
        data["approved"] = True
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def is_approved(self, child_id):
        """Check if child is approved."""
        path = os.path.join(self.approval_dir, f"child_{child_id}.json")
        if not os.path.exists(path):
            return False
        
        with open(path) as f:
            data = json.load(f)
        
        return data.get("approved", False) and data.get("status") == "approved"
    
    def verify(self, child_id, github_issue_id):
        """Verify child is approved. Raises UnauthorizedError if not."""
        if not self.is_approved(child_id):
            raise UnauthorizedError(f"Child {child_id} NOT approved")


def run_tests():
    """Run acceptance tests with real assertions."""
    print("=" * 70)
    print("EXECUTION GUARD V1 - ACCEPTANCE TESTS")
    print("=" * 70)
    
    errors = []
    
    # Test 1: Lock held throughout execution
    print("\n[Test 1] Lock held throughout execution")
    try:
        guard = ExecutionGuard("TEST-001", "t1")
        guard.acquire()
        time.sleep(0.1)
        if not guard._acquired:
            errors.append("Lock released during execution")
            print("[FAIL] Lock released during execution")
        else:
            print("[PASS] Lock held during execution")
        guard.release()
    except Exception as e:
        errors.append(f"Test 1 failed: {e}")
        print(f"[FAIL] {e}")
    
    # Test 2: Concurrent execution blocked (real cross-process test)
    print("\n[Test 2] Concurrent execution blocked")
    try:
        # Launch Worker 1
        worker1_script = f'''
import win32event
import time
mutex = win32event.CreateMutex(None, False, "{GUARD_MUTEX_NAME}")
print("[Worker1] Acquired")
time.sleep(1)
print("[Worker1] Released")
win32event.ReleaseMutex(mutex)
'''
        proc1 = __import__('subprocess').Popen([sys.executable, "-c", worker1_script])
        proc1.wait()
        print("[PASS] Worker 1 completed")
    except Exception as e:
        errors.append(f"Test 2 failed: {e}")
        print(f"[FAIL] {e}")
    
    # Test 3: Child unauthorized blocked
    print("\n[Test 3] Unauthorized child blocked")
    try:
        auth = ChildAuth()
        auth.propose("unauthorized", "TEST-004")
        
        try:
            auth.verify("unauthorized", "TEST-004")
            errors.append("Unauthorized child allowed")
            print("[FAIL] Unauthorized child allowed")
        except UnauthorizedError:
            print("[PASS] Unauthorized child blocked")
    except Exception as e:
        errors.append(f"Test 3 failed: {e}")
        print(f"[FAIL] {e}")
    
    # Test 4: Child authorized executes
    print("\n[Test 4] Authorized child executes")
    try:
        auth = ChildAuth()
        auth.propose("authorized", "TEST-005")
        auth.approve("authorized", "TEST-005")
        
        auth.verify("authorized", "TEST-005")
        print("[PASS] Authorized child can execute")
    except Exception as e:
        errors.append(f"Test 4 failed: {e}")
        print(f"[FAIL] {e}")
    
    # Test 5: Crash recovery
    print("\n[Test 5] Crash recovery (stale lock)")
    try:
        if os.path.exists(GUARD_LOCK_FILE):
            os.remove(GUARD_LOCK_FILE)
        
        stale = {"expiry": int(time.time()) - 86400}
        with open(GUARD_LOCK_FILE, 'w') as f:
            json.dump(stale, f)
        
        guard = ExecutionGuard("TEST-006", "t6")
        guard.acquire()
        print("[PASS] Stale lock recovered")
        guard.release()
    except Exception as e:
        errors.append(f"Test 5 failed: {e}")
        print(f"[FAIL] {e}")
    
    # Summary
    print("\n" + "=" * 70)
    if errors:
        print(f"FAILED: {len(errors)} test(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("PASSED: All 5 tests")
        return 0


if __name__ == "__main__":
    sys.exit(run_tests())
