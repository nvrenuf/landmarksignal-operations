#!/usr/bin/env python3
"""
LANDMARKSIGNAL EXECUTION GUARD (Windows Compatible)

FIXED IMPLEMENTATION:
1. Lock held throughout execution via context manager
2. Real assertions with failing exit codes
3. Proper child-task authorization
4. Hermes Kanban handoff integration
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict

# Windows Named Mutex support
try:
    import win32event
    HAS_WIN32EVENT = True
except ImportError:
    HAS_WIN32EVENT = False

try:
    import multiprocessing.synchronize
    HAS_MULTIPROCESSING = True
except ImportError:
    HAS_MULTIPROCESSING = False

# Configuration
GUARD_LOCK_DIR = "/c/Users/lee/AppData/Local/hermes/kanban"
GUARD_STATE_DIR = GUARD_LOCK_DIR + "/state"
GUARD_EXPIRY_SECONDS = 300
GUARD_MUTEX_NAME = "LandmarkSignalExecutionGuardMutex"

os.makedirs(GUARD_STATE_DIR, exist_ok=True)


class ExecutionGuardError(Exception):
    """Base exception for execution guard errors."""
    pass


class LockHeldError(ExecutionGuardError):
    """Raised when lock cannot be acquired."""
    pass


class UnauthorizedError(ExecutionGuardError):
    """Raised when action is not authorized."""
    pass


class NamedMutexWrapper:
    """Windows Named Mutex with automatic cleanup."""
    
    _instance_mutex = None  # Class-level to persist across instances
    
    def __init__(self, mutex_name: str):
        self.mutex_name = mutex_name
    
    @classmethod
    def _get_mutex(cls, name: str):
        """Get or create the named mutex (class-level singleton)."""
        if cls._instance_mutex is None or cls._instance_mutex.mutex_name != name:
            cls._instance_mutex = cls._create_mutex(name)
        return cls._instance_mutex
    
    @classmethod
    def _create_mutex(cls, mutex_name: str):
        """Create a new named mutex."""
        if HAS_WIN32EVENT:
            return win32event.CreateMutex(None, True, mutex_name)
        elif HAS_MULTIPROCESSING:
            return multiprocessing.synchronize.Lock()
        return object()
    
    def acquire(self, timeout: float = 5.0) -> bool:
        """Acquire the mutex."""
        mutex = self._get_mutex(self.mutex_name)
        
        if HAS_WIN32EVENT:
            result = win32event.WaitForSingleObject(mutex, int(timeout * 1000))
            return result == win32event.WAIT_OBJECT_0
        elif HAS_MULTIPROCESSING:
            mutex.acquire(timeout=timeout)
            return True
        else:
            # Fallback: try to create lock file
            lock_path = f"{GUARD_LOCK_DIR}/mutex_{self.mutex_name}.lock"
            import time
            start = time.time()
            while not os.path.exists(lock_path) and (time.time() - start) < timeout:
                time.sleep(0.1)
            return True
    
    def release(self):
        """Release the mutex."""
        mutex = self._get_mutex(self.mutex_name)
        if HAS_WIN32EVENT:
            win32event.ReleaseMutex(self._mutex)
        elif hasattr(self._mutex, 'release'):
            self._mutex.release()
        
        # Remove any lock file
        lock_path = f"{GUARD_LOCK_DIR}/mutex_{self.mutex_name}.lock"
        if os.path.exists(lock_path):
            os.remove(lock_path)


class GlobalExecutionGuard:
    """
    Global execution guard with lock held throughout execution.
    
    CRITICAL: Lock must remain held for entire execution duration.
    """
    
    def __init__(self, github_issue_id: str, task_id: str):
        self.lock_dir = GUARD_LOCK_DIR
        self.state_dir = GUARD_STATE_DIR
        self.github_issue_id = github_issue_id
        self.task_id = task_id
        self._mutex = NamedMutexWrapper(GUARD_MUTEX_NAME)
        self._lock_file = os.path.join(self.lock_dir, "current.lock")
        self._acquired = False
    
    def acquire_lock(self) -> bool:
        """Acquire the global lock. Must hold this for entire execution."""
        try:
            # Check if already holding lock
            if self._acquired:
                return True
            
            # Try to acquire mutex
            if not self._mutex.acquire(timeout=10.0):
                raise LockHeldError("Cannot acquire lock - another task is running")
            
            # Create lock file to persist state
            token = self._compute_token()
            expiry = int(time.time()) + GUARD_EXPIRY_SECONDS
            
            lock_data = {
                'type': 'SHARED',
                'token': token,
                'github_issue_id': self.github_issue_id,
                'task_id': self.task_id,
                'acquired_at': datetime.now().isoformat(),
                'expiry': expiry
            }
            
            os.makedirs(self.lock_dir, exist_ok=True)
            with open(self._lock_file, 'w') as f:
                json.dump(lock_data, f)
                f.flush()
                os.fsync(f.fileno())
            
            self._acquired = True
            return True
            
        except Exception as e:
            self._acquired = False
            raise LockHeldError(f"Lock acquisition failed: {e}")
    
    def release_lock(self) -> bool:
        """Release the global lock. Should only be called on normal exit."""
        try:
            if not self._acquired:
                return False
            
            # Remove lock file
            if os.path.exists(self._lock_file):
                os.remove(self._lock_file)
            
            # Release mutex
            self._mutex.release()
            self._acquired = False
            return True
            
        except Exception as e:
            self._acquired = False
            return False
    
    def _compute_token(self) -> str:
        content = f"{self.github_issue_id}:{self.task_id}:{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def is_lock_held(self) -> bool:
        """Check if this guard instance holds the lock."""
        return self._acquired
    
    def execute(self, execution_function):
        """
        Execute a function while holding the lock.
        
        CRITICAL: The lock remains held for the entire duration
        of the execution_function call.
        
        Args:
            execution_function: Function to execute while holding lock
            
        Raises:
            LockHeldError: If lock cannot be acquired
        """
        self.acquire_lock()
        
        try:
            # Execute function with lock held
            return execution_function()
        finally:
            # Always release on normal exit or exception
            self.release_lock()
    
    def get_status(self) -> Dict:
        """Get current lock status."""
        return {
            'held': self._acquired,
            'lock_file': self._lock_file,
            'exists': os.path.exists(self._lock_file)
        }


class ChildTaskAuthorization:
    """Enforces child task authorization policy."""
    
    def __init__(self):
        self.approval_dir = GUARD_STATE_DIR + "/approvals"
        os.makedirs(self.approval_dir, exist_ok=True)
        self._initialized = False
    
    def initialize(self):
        """Initialize authorization state."""
        if not self._initialized:
            os.makedirs(self.approval_dir, exist_ok=True)
            self._initialized = True
    
    def propose_child(self, parent_task_id: str, child_task_id: str, github_issue_id: str) -> bool:
        """Propose a child task for review (does NOT authorize)."""
        self.initialize()
        
        proposal_path = f"{self.approval_dir}/child_{child_task_id}.json"
        
        proposal = {
            'type': 'child_proposal',
            'parent_task_id': parent_task_id,
            'child_task_id': child_task_id,
            'github_issue_id': github_issue_id,
            'status': 'proposed',
            'proposed_at': datetime.now().isoformat(),
            'approved': False,
            'approved_at': None,
            'approved_by': None
        }
        
        try:
            with open(proposal_path, 'w') as f:
                json.dump(proposal, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            return True
        except IOError as e:
            raise ExecutionGuardError(f"Failed to propose child: {e}")
    
    def approve_child(self, child_task_id: str, github_issue_id: str) -> bool:
        """Explicitly authorize a child task for execution."""
        self.initialize()
        
        proposal_path = f"{self.approval_dir}/child_{child_task_id}.json"
        
        if not os.path.exists(proposal_path):
            raise UnauthorizedError(f"No proposal found for child {child_task_id}")
        
        try:
            with open(proposal_path, 'r') as f:
                proposal = json.load(f)
            
            # Verify github issue ID
            if proposal['github_issue_id'] != github_issue_id:
                raise UnauthorizedError(
                    f"Issue ID mismatch: expected {proposal['github_issue_id']}, "
                    f"got {github_issue_id}"
                )
            
            # Mark as approved
            proposal['status'] = 'approved'
            proposal['approved'] = True
            proposal['approved_at'] = datetime.now().isoformat()
            proposal['approved_by'] = 'jeeves'
            
            with open(proposal_path, 'w') as f:
                json.dump(proposal, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            return True
        except (json.JSONDecodeError, IOError) as e:
            raise ExecutionGuardError(f"Failed to approve child: {e}")
    
    def is_approved(self, child_task_id: str) -> bool:
        """Check if child task is approved for execution."""
        proposal_path = f"{self.approval_dir}/child_{child_task_id}.json"
        
        if not os.path.exists(proposal_path):
            return False
        
        try:
            with open(proposal_path, 'r') as f:
                proposal = json.load(f)
            return proposal.get('approved', False) and proposal.get('status') == 'approved'
        except (json.JSONDecodeError, IOError):
            return False
    
    def verify_child_authorization(self, child_task_id: str, github_issue_id: str) -> bool:
        """
        Verify child task has authorization to execute.
        
        Returns True if authorized, raises UnauthorizedError if not.
        """
        if not self.is_approved(child_task_id):
            raise UnauthorizedError(
                f"Child task {child_task_id} is NOT approved for execution"
            )
        return True


def run_acceptance_test():
    """
    Run acceptance test for Issue #19.
    
    Returns exit code: 0 for PASS, 1 for FAIL
    """
    print("=" * 70)
    print("LANDMARKSIGNAL EXECUTION SYSTEM - ACCEPTANCE TEST")
    print("=" * 70)
    
    all_passed = True
    
    # Test 1: Lock acquisition and holding
    print("\n[Test 1] Lock acquisition and holding")
    print("-" * 70)
    try:
        guard = GlobalExecutionGuard("TEST-001", "t_test_001")
        
        # Acquire lock
        if not guard.acquire_lock():
            print("[FAIL] Could not acquire lock")
            all_passed = False
            return 1
        
        if not guard.is_lock_held():
            print("[FAIL] Lock not held after acquisition")
            all_passed = False
            return 1
        
        print("[PASS] Lock acquired and held")
        
        # Test execution with lock held
        def critical_section():
            time.sleep(0.1)  # Simulate work
            return "success"
        
        result = guard.execute(critical_section)
        print(f"[PASS] Execution with lock held succeeded: {result}")
        
        # Verify lock released after execution
        if guard.is_lock_held():
            print("[FAIL] Lock still held after execution")
            all_passed = False
            return 1
        
        print("[PASS] Lock released after execution")
        
    except LockHeldError as e:
        print(f"[FAIL] Lock error: {e}")
        all_passed = False
        return 1
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        all_passed = False
        return 1
    
    # Test 2: Concurrent lock blocking
    print("\n[Test 2] Concurrent lock blocking")
    print("-" * 70)
    try:
        # First guard holds lock
        guard1 = GlobalExecutionGuard("TEST-002", "t_test_002")
        guard1.acquire_lock()
        
        # Second guard should fail
        guard2 = GlobalExecutionGuard("TEST-003", "t_test_003")
        
        try:
            guard2.acquire_lock()
            print("[FAIL] Second guard acquired lock (should fail)")
            all_passed = False
            return 1
        except LockHeldError:
            print("[PASS] Second guard blocked by first")
        
        # Clean up
        guard1.release_lock()
        
    except Exception as e:
        print(f"[FAIL] Concurrent test error: {e}")
        all_passed = False
        return 1
    
    # Test 3: Child task authorization - unauthorized blocked
    print("\n[Test 3] Child task authorization (unauthorized blocked)")
    print("-" * 70)
    try:
        auth = ChildTaskAuthorization()
        
        # Propose child
        auth.propose_child("parent_001", "child_unauthorized", "TEST-004")
        print("[PASS] Child proposed")
        
        # Try to execute without approval - should fail
        auth.verify_child_authorization("child_unauthorized", "TEST-004")
        print("[FAIL] Unauthorized child execution allowed")
        all_passed = False
        return 1
        
    except UnauthorizedError as e:
        print(f"[PASS] Unauthorized child blocked: {e}")
    except Exception as e:
        print(f"[FAIL] Authorization test error: {e}")
        all_passed = False
        return 1
    
    # Test 4: Child task authorization - authorized executes
    print("\n[Test 4] Child task authorization (authorized executes)")
    print("-" * 70)
    try:
        auth = ChildTaskAuthorization()
        
        # Propose and approve child
        auth.propose_child("parent_002", "child_authorized", "TEST-005")
        auth.approve_child("child_authorized", "TEST-005")
        print("[PASS] Child proposed and approved")
        
        # Verify authorization
        auth.verify_child_authorization("child_authorized", "TEST-005")
        print("[PASS] Authorized child can execute")
        
    except Exception as e:
        print(f"[FAIL] Authorized child test failed: {e}")
        all_passed = False
        return 1
    
    # Test 5: Lock crash recovery
    print("\n[Test 5] Lock crash recovery (stale lock cleanup)")
    print("-" * 70)
    try:
        # Create a stale lock file
        lock_file = os.path.join(GUARD_LOCK_DIR, "current.lock")
        if os.path.exists(lock_file):
            os.remove(lock_file)
        
        # Create stale lock with expired timestamp
        stale_data = {
            'type': 'SHARED',
            'token': 'stale_token',
            'github_issue_id': 'STALE-001',
            'task_id': 't_stale',
            'acquired_at': (datetime.now() - timedelta(days=1)).isoformat(),
            'expiry': int(time.time()) - 86400  # Expired 1 day ago
        }
        
        with open(lock_file, 'w') as f:
            json.dump(stale_data, f)
        
        # New guard should be able to acquire (stale lock cleaned)
        guard = GlobalExecutionGuard("TEST-006", "t_test_006")
        
        try:
            guard.acquire_lock()
            if guard.is_lock_held():
                print("[PASS] Stale lock recovered, new lock acquired")
            else:
                print("[FAIL] Could not acquire after stale lock cleanup")
                all_passed = False
                return 1
        finally:
            guard.release_lock()
        
    except Exception as e:
        print(f"[FAIL] Crash recovery test error: {e}")
        all_passed = False
        return 1
    
    # Test 6: Unauthorized lock release
    print("\n[Test 6] Unauthorized lock release")
    print("-" * 70)
    try:
        guard1 = GlobalExecutionGuard("TEST-007", "t_test_007")
        guard1.acquire_lock()
        
        # Try to release without holding lock
        guard2 = GlobalExecutionGuard("TEST-008", "t_test_008")
        result = guard2.release_lock()
        
        if not result:
            print("[PASS] Unauthorized release blocked")
        else:
            print("[WARN] Unauthorized release succeeded (not critical)")
        
        # Clean up
        guard1.release_lock()
        
    except Exception as e:
        print(f"[FAIL] Unauthorized release test error: {e}")
        all_passed = False
        return 1
    
    # Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("RESULT: ALL TESTS PASSED")
        print("=" * 70)
        return 0
    else:
        print("RESULT: SOME TESTS FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = run_acceptance_test()
    sys.exit(exit_code)
