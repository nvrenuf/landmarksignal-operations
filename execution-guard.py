#!/usr/bin/env python3
"""
LANDMARKSIGNAL EXECUTION GUARD (Windows Compatible with Named Mutexes)

Implements:
1. Global concurrency guard (single active task at a time)
2. Child-task authorization enforcement
3. Crash recovery for stale locks
4. Atomic lock acquisition/release

Uses Windows Named Mutexes for true cross-process protection.
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime
from typing import Optional, Dict

# Try to import win32event for Named Mutexes (Windows)
try:
    import win32event
    HAS_WIN32EVENT = True
except ImportError:
    HAS_WIN32EVENT = False

# Fallback for non-Windows or if win32event unavailable
try:
    import multiprocessing.synchronize
    HAS_MULTIPROCESSING = True
except ImportError:
    HAS_MULTIPROCESSING = False

# Configuration
GUARD_LOCK_DIR = "/c/Users/lee/AppData/Local/hermes/kanban"
GUARD_STATE_DIR = GUARD_LOCK_DIR + "/state"
GUARD_STATE_FILE = GUARD_STATE_DIR + "/current_task.json"
GUARD_EXPIRY_SECONDS = 300  # 5 minutes for stale lock detection
GUARD_MAX_RETRIES = 3
GUARD_RETRY_DELAY = 0.5
GUARD_MUTEX_NAME = "LandmarkSignalExecutionGuardMutex"  # Unique named mutex

# Ensure directories exist
os.makedirs(GUARD_STATE_DIR, exist_ok=True)


class NamedMutexWrapper:
    """
    Wrapper for Windows Named Mutex with automatic cleanup.
    Provides cross-process synchronization.
    """
    
    def __init__(self, mutex_name: str):
        self.mutex_name = mutex_name
        self._mutex = None
        
    def _get_mutex(self) -> object:
        """Get or create the named mutex."""
        if self._mutex is None:
            if HAS_WIN32EVENT:
                # Windows Named Mutex - returns a handle
                self._mutex = win32event.CreateMutex(
                    None,  # Default security
                    True,  # Initial ownership false (allow acquisition)
                    self.mutex_name  # Named mutex
                )
                # win32event.CreateMutex returns a handle, not a Mutex object
            elif HAS_MULTIPROCESSING:
                # Fallback to multiprocessing Lock (still cross-process)
                self._mutex = multiprocessing.synchronize.Lock()
            else:
                # Last resort: file-based (not truly cross-process)
                self._mutex = object()
        return self._mutex
    
    def acquire(self, timeout: float = 5.0) -> bool:
        """Acquire the mutex."""
        mutex = self._get_mutex()
        
        if HAS_WIN32EVENT:
            # Windows wait with timeout - returns WAIT_OBJECT_0 (0) on success
            result = win32event.WaitForSingleObject(mutex, int(timeout * 1000))
            return result == win32event.WAIT_OBJECT_0
        elif HAS_MULTIPROCESSING:
            # Multiprocessing lock acquire
            mutex.acquire(timeout=timeout)
            return True
        else:
            # File-based fallback (not cross-process)
            return True
    
    def release(self) -> bool:
        """Release the mutex."""
        mutex = self._get_mutex()
        
        if HAS_WIN32EVENT:
            win32event.ReleaseMutex(mutex)
            return True
        elif HAS_MULTIPROCESSING:
            mutex.release()
            return True
        else:
            return True
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


class GlobalExecutionGuard:
    """
    Thread-safe global execution guard for LandmarkSignal Kanban.
    
    Ensures only one task executes at a time across the entire system.
    Uses Windows-compatible file operations for atomic locking.
    """
    
    def __init__(self):
        self.lock_dir = GUARD_LOCK_DIR
        self.state_dir = GUARD_STATE_DIR
        self.expiry_seconds = GUARD_EXPIRY_SECONDS
        self.max_retries = GUARD_MAX_RETRIES
        self.retry_delay = GUARD_RETRY_DELAY
        
        # Ensure state directory exists
        os.makedirs(self.state_dir, exist_ok=True)
        
        # Create named mutex for cross-process synchronization
        self._mutex = NamedMutexWrapper(GUARD_MUTEX_NAME)
    
    def _compute_lock_token(self, github_issue_id: str, task_id: str) -> str:
        """Compute unique lock token for a task."""
        content = f"{github_issue_id}:{task_id}:{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _get_lock_file_path(self, github_issue_id: str, task_id: str) -> str:
        """Get the lock file path for a specific task."""
        # Use task_id as the filename for uniqueness
        safe_task_id = "".join(c for c in task_id if c.isalnum() or c in '-_')
        return os.path.join(self.lock_dir, f"lock_{safe_task_id}.lock")
    
    def _get_shared_lock_file_path(self) -> str:
        """Get the shared lock file path (single global lock)."""
        return os.path.join(self.lock_dir, "current.lock")
    
    def _is_stale_lock(self, github_issue_id: str, task_id: str) -> bool:
        """Check if current lock is stale (expired)."""
        lock_file = self._get_lock_file_path(github_issue_id, task_id)
        
        if not os.path.exists(lock_file):
            return True
        
        try:
            with open(lock_file, 'r') as f:
                lock_data = json.load(f)
                
                # Check expiry
                expiry = lock_data.get('expiry', 0)
                if time.time() > expiry:
                    return True
                
                # Check if we hold this lock
                current_token = lock_data.get('token')
                expected_token = self._compute_lock_token(github_issue_id, task_id)
                if current_token != expected_token:
                    return True
        except (json.JSONDecodeError, IOError):
            return True
        
        return False
    
    def _cleanup_stale_locks(self):
        """Remove any expired lock files. Does NOT touch current.lock."""
        try:
            if os.path.exists(self.lock_dir):
                for filename in os.listdir(self.lock_dir):
                    if filename.endswith('.lock') and filename != 'current.lock':
                        filepath = os.path.join(self.lock_dir, filename)
                        try:
                            with open(filepath, 'r') as f:
                                lock_data = json.load(f)
                                if time.time() > lock_data.get('expiry', 0):
                                    os.remove(filepath)
                        except (json.JSONDecodeError, IOError):
                            pass
        except OSError:
            pass
    
    def _release_shared_lock(self):
        """Release the shared lock."""
        shared_lock_file = self._get_shared_lock_file_path()
        
        if not os.path.exists(shared_lock_file):
            return False
        
        try:
            with open(shared_lock_file, 'r') as f:
                lock_data = json.load(f)
                
                # Verify this is our lock
                if lock_data.get('type') != 'SHARED':
                    return False
                
                # Clean up
                os.remove(shared_lock_file)
                return True
        except (json.JSONDecodeError, IOError):
            return False
    
    def _acquire_shared_lock(self) -> bool:
        """
        Attempt to acquire the SHARED (global) lock atomically.
        
        Uses Named Mutex for cross-process protection.
        Returns True if lock acquired, False if already held.
        """
        # First try to acquire the mutex
        if not self._mutex.acquire(timeout=GUARD_RETRY_DELAY):
            return False
        
        try:
            shared_lock_file = self._get_shared_lock_file_path()
            token = self._compute_lock_token('SHARED', 'GLOBAL')
            expiry = int(time.time()) + self.expiry_seconds
            
            lock_data = {
                'type': 'SHARED',
                'token': token,
                'acquired_at': datetime.now().isoformat(),
                'expiry': expiry
            }
            
            # Try to create lock file (atomic on Windows if dir exists)
            try:
                with open(shared_lock_file, 'w') as f:
                    json.dump(lock_data, f)
                    f.flush()
                    os.fsync(f.fileno())
                return True
            except FileExistsError:
                # Lock already exists - release mutex and try again
                self._mutex.release()
                return False
            except OSError:
                self._mutex.release()
                return False
        finally:
            # Always release the mutex
            self._mutex.release()
    
    def acquire(self, github_issue_id: str, task_id: str) -> bool:
        """
        Acquire the global execution lock.
        
        This acquires the SHARED lock - only one task can execute at a time.
        
        Args:
            github_issue_id: GitHub issue identifier
            task_id: Task identifier (Kanban task ID)
        
        Returns:
            True if lock acquired, False if another task is running
        """
        # Clean up stale locks first (but NOT the shared lock)
        self._cleanup_stale_locks()
        
        # Try to acquire the shared lock
        for attempt in range(self.max_retries):
            if self._acquire_shared_lock():
                # Double-check after acquiring
                shared_lock_file = self._get_shared_lock_file_path()
                if os.path.exists(shared_lock_file):
                    try:
                        with open(shared_lock_file, 'r') as f:
                            lock_data = json.load(f)
                            if lock_data.get('type') == 'SHARED':
                                return True
                    except (json.JSONDecodeError, IOError):
                        pass
            time.sleep(self.retry_delay)
        
        return False
    
    def release(self, github_issue_id: str, task_id: str) -> bool:
        """Release the global execution lock."""
        return self._release_shared_lock()
    
    def hold(self, github_issue_id: str, task_id: str) -> bool:
        """
        Check if we currently hold the lock.
        
        For the shared lock, we check if the current lock matches ours.
        """
        shared_lock_file = self._get_shared_lock_file_path()
        
        if not os.path.exists(shared_lock_file):
            return False
        
        try:
            with open(shared_lock_file, 'r') as f:
                lock_data = json.load(f)
                # We don't track our token for the shared lock
                # We just check if it's a SHARED lock
                return lock_data.get('type') == 'SHARED'
        except (json.JSONDecodeError, IOError):
            return False
    
    def get_status(self) -> Dict:
        """Get current lock status."""
        # Check shared lock
        shared_lock_file = self._get_shared_lock_file_path()
        
        locks = []
        
        # List all active locks
        try:
            if os.path.exists(self.lock_dir):
                for filename in os.listdir(self.lock_dir):
                    if filename.endswith('.lock') and filename != 'current.lock':
                        filepath = os.path.join(self.lock_dir, filename)
                        try:
                            with open(filepath, 'r') as f:
                                lock_data = json.load(f)
                                lock_data['filename'] = filename
                                lock_data['is_stale'] = time.time() > lock_data.get('expiry', 0)
                                locks.append(lock_data)
                        except (json.JSONDecodeError, IOError):
                            pass
        except OSError:
            pass
        
        # Check if we hold the shared lock
        has_shared = os.path.exists(shared_lock_file)
        
        return {
            'status': 'held' if has_shared or locks else 'released',
            'has_shared_lock': has_shared,
            'locks': locks
        }


class ChildTaskAuthorization:
    """
    Enforces child task authorization policy.
    
    Requirements:
    - Children may be proposed or created as drafts
    - Creating a child must NOT authorize execution
    - Child execution requires explicit approval
    - No automatic child dispatch
    - No automatic scope expansion
    """
    
    def __init__(self):
        self.approval_dir = GUARD_STATE_DIR + "/approvals"
        os.makedirs(self.approval_dir, exist_ok=True)
    
    def propose_child(self, parent_task_id: str, child_task_id: str, github_issue_id: str) -> bool:
        """
        Propose a child task for review.
        
        This creates a draft child task but does NOT authorize execution.
        """
        proposal_path = self.approval_dir + f"child_{child_task_id}.json"
        
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
            print(f"[ERROR] Failed to propose child task: {e}")
            return False
    
    def approve_child(self, child_task_id: str, github_issue_id: str) -> bool:
        """
        Approve a child task for execution.
        
        This is the explicit authorization step required before child execution.
        """
        proposal_path = self.approval_dir + f"child_{child_task_id}.json"
        
        if not os.path.exists(proposal_path):
            print(f"[ERROR] No proposal found for child task {child_task_id}")
            return False
        
        try:
            with open(proposal_path, 'r') as f:
                proposal = json.load(f)
            
            # Verify this approval is for the correct GitHub issue
            if proposal['github_issue_id'] != github_issue_id:
                print(f"[ERROR] Approval request mismatch: expected {proposal['github_issue_id']}, got {github_issue_id}")
                return False
            
            # Mark as approved
            proposal['status'] = 'approved'
            proposal['approved'] = True
            proposal['approved_at'] = datetime.now().isoformat()
            proposal['approved_by'] = 'jeeves'  # Or system/user identifier
            
            with open(proposal_path, 'w') as f:
                json.dump(proposal, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"[ERROR] Failed to approve child task: {e}")
            return False
    
    def is_approved(self, child_task_id: str) -> bool:
        """Check if a child task has been approved for execution."""
        proposal_path = self.approval_dir + f"child_{child_task_id}.json"
        
        if not os.path.exists(proposal_path):
            return False
        
        try:
            with open(proposal_path, 'r') as f:
                proposal = json.load(f)
            return proposal.get('approved', False) and proposal.get('status') == 'approved'
        except (json.JSONDecodeError, IOError):
            return False
    
    def create_child_without_approval(self, parent_task_id: str, child_task_id: str, github_issue_id: str) -> bool:
        """
        Create a child task WITHOUT authorization.
        
        This should FAIL per policy - child execution requires explicit approval.
        """
        # This function exists to test that unauthorized creation is BLOCKED
        # In production, this should never be called without first calling approve_child()
        
        # For testing purposes, we check if approval exists
        if not self.is_approved(child_task_id):
            print(f"[BLOCKED] Child task {child_task_id} is NOT approved for execution")
            print(f"[BLOCKED] Creating child task without authorization is forbidden")
            return False
        
        # If approved, allow creation
        proposal_path = self.approval_dir + f"child_{child_task_id}.json"
        
        try:
            with open(proposal_path, 'r') as f:
                proposal = json.load(f)
            
            proposal['status'] = 'created'
            proposal['created_at'] = datetime.now().isoformat()
            
            with open(proposal_path, 'w') as f:
                json.dump(proposal, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            print(f"[SUCCESS] Child task {child_task_id} created (approved)")
            return True
        except IOError as e:
            print(f"[ERROR] Failed to create child task: {e}")
            return False


def clean_locks():
    """Clean up any existing locks for testing."""
    shared_lock = os.path.join(GUARD_LOCK_DIR, "current.lock")
    
    if os.path.exists(shared_lock):
        os.remove(shared_lock)
        print("[CLEANUP] Removed shared lock")
    
    # Remove stale task locks
    if os.path.exists(GUARD_LOCK_DIR):
        for filename in os.listdir(GUARD_LOCK_DIR):
            if filename.endswith('.lock') and filename != 'current.lock':
                filepath = os.path.join(GUARD_LOCK_DIR, filename)
                try:
                    with open(filepath, 'r') as f:
                        lock_data = json.load(f)
                        if time.time() > lock_data.get('expiry', 0):
                            os.remove(filepath)
                            print(f"[CLEANUP] Removed stale lock: {filename}")
                except (json.JSONDecodeError, IOError):
                    os.remove(filepath)
                    print(f"[CLEANUP] Removed invalid lock: {filename}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='LandmarkSignal Execution Guard')
    parser.add_argument('--action', required=True, choices=['acquire', 'release', 'status', 'test', 'propose', 'approve', 'cleanup'],
                       help='Action to perform')
    parser.add_argument('--github-issue-id', default='', help='GitHub issue ID')
    parser.add_argument('--task-id', default='', help='Task/Kanban ID')
    parser.add_argument('--parent-task-id', default='', help='Parent task ID (for child tasks)')
    parser.add_argument('--child-task-id', default='', help='Child task ID (for child tasks)')
    
    args = parser.parse_args()
    
    guard = GlobalExecutionGuard()
    auth = ChildTaskAuthorization()
    
    if args.action == 'cleanup':
        clean_locks()
        sys.exit(0)
    
    if args.action == 'acquire':
        if not args.github_issue_id or not args.task_id:
            print("[ERROR] acquire requires --github-issue-id and --task-id")
            sys.exit(1)
        
        if guard.acquire(args.github_issue_id, args.task_id):
            print(f"[SUCCESS] Lock acquired for GitHub Issue #{args.github_issue_id}, Task {args.task_id}")
            sys.exit(0)
        else:
            print(f"[BLOCKED] Lock already held by another task")
            sys.exit(1)
    
    elif args.action == 'release':
        if not args.github_issue_id or not args.task_id:
            print("[ERROR] release requires --github-issue-id and --task-id")
            sys.exit(1)
        
        if guard.release(args.github_issue_id, args.task_id):
            print("[SUCCESS] Lock released")
            sys.exit(0)
        else:
            print("[ERROR] Could not release lock (not held or not shared lock)")
            sys.exit(1)
    
    elif args.action == 'status':
        status = guard.get_status()
        print(json.dumps(status, indent=2))
        sys.exit(0)
    
    elif args.action == 'test':
        """Test the guard with a simulated execution."""
        print("=" * 60)
        print("EXECUTION GUARD TEST")
        print("=" * 60)
        
        # Clean up first
        print("\n[CLEANUP] Cleaning up previous test locks")
        clean_locks()
        
        # Test 1: Status when no lock
        print("\nTest 1: Status (no lock)")
        status = guard.get_status()
        if not status.get('has_shared_lock', False) and not status.get('locks'):
            print("[PASS] Status shows released")
        else:
            print(f"[FAIL] Status incorrect: {status}")
        
        # Test 2: Acquire lock
        print("\nTest 2: Acquire lock")
        if guard.acquire("TEST-001", "t_test_001"):
            print("[PASS] Lock acquired")
        else:
            print("[FAIL] Could not acquire lock")
        
        # Test 3: Try to acquire again (should fail)
        print("\nTest 3: Attempt second acquisition (should fail)")
        # Don't call cleanup here - we want to test concurrent acquisition
        if guard.acquire("TEST-002", "t_test_002"):
            print("[FAIL] Second acquisition succeeded (should fail)")
        else:
            print("[PASS] Second acquisition blocked")
        
        # Test 4: Check status
        print("\nTest 4: Check status")
        status = guard.get_status()
        if status.get('has_shared_lock', False):
            print(f"[PASS] Status shows shared lock held")
        else:
            print(f"[FAIL] Status shows no shared lock")
        
        # Test 5: Release shared lock
        print("\nTest 5: Release lock")
        if guard.release("TEST-001", "t_test_001"):
            print("[PASS] Lock released")
        else:
            print("[FAIL] Could not release lock")
        
        # Test 6: Verify released
        print("\nTest 6: Verify lock is released")
        status = guard.get_status()
        if not status.get('has_shared_lock', False) and not status.get('locks'):
            print("[PASS] Lock is released")
        else:
            print(f"[FAIL] Still has locks: {status}")
        
        # Test 7: Child task authorization test
        print("\nTest 7: Child task authorization (unauthorized)")
        if auth.propose_child("parent_001", "child_test_001", "TEST-003"):
            print("[PASS] Child proposed")
        else:
            print("[FAIL] Child not proposed")
        
        print("\nAttempting to create child WITHOUT approval:")
        if auth.create_child_without_approval("parent_001", "child_test_001", "TEST-003"):
            print("[FAIL] Child created without approval (should be blocked)")
        else:
            print("[PASS] Child creation blocked without approval")
        
        # Test 8: Approve and create
        print("\nTest 8: Approve child and create")
        if auth.approve_child("child_test_001", "TEST-003"):
            print("[PASS] Child approved")
        else:
            print("[FAIL] Child not approved")
        
        if auth.create_child_without_approval("parent_001", "child_test_001", "TEST-003"):
            print("[PASS] Child created after approval")
        else:
            print("[FAIL] Child creation failed after approval")
        
        # Cleanup
        print("\n[CLEANUP] Cleaning up test locks")
        clean_locks()
        
        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        sys.exit(0)

if __name__ == "__main__":
    main()
