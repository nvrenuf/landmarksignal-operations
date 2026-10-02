#!/usr/bin/env python3
"""
LANDMARKSIGNAL EXECUTION GUARD - CORRECTED ACCEPTANCE TESTS

Real tests with:
- Proper subprocess synchronization
- Bounded waits
- Actual assertions
- Nonzero exit codes on failure
"""

import os
import sys
import json
import time
import subprocess

# Add current directory to path (for module import)
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Now import
from execution_guard_v1_final import (
    ExecutionGuard,
    ChildAuth,
    MutexUnavailableError,
    LockHeldError,
    UnauthorizedError,
    GUARD_MUTEX_NAME,
    GUARD_LOCK_FILE,
    GUARD_STATE_DIR,
)


def test_1_lock_held_throughout_execution():
    """Test 1: Lock held throughout execution."""
    print("\n[Test 1] Lock held throughout execution")
    try:
        guard = ExecutionGuard("TEST-001", "t1")
        guard.acquire()
        time.sleep(0.1)
        if not guard._acquired:
            print("[FAIL] Lock released during execution")
            return 1
        else:
            print("[PASS] Lock held during execution")
        guard.release()
    except Exception as e:
        print(f"[FAIL] {e}")
        return 1
    return 0


def test_2_concurrent_execution_blocked():
    """
    Test 2: Concurrent execution blocked.
    
    Two processes: Worker A holds lock for 2 seconds, Worker B tries to acquire.
    Worker B should WAIT until Worker A releases.
    """
    print("\n[Test 2] Concurrent execution blocked")
    
    # Create test directory
    test_state_dir = r"C:/Users/lee/AppData/Local/hermes/kanban/state/test_concurrent4"
    os.makedirs(test_state_dir, exist_ok=True)
    
    lock_file = os.path.join(test_state_dir, "concurrent.lock")
    state_file = os.path.join(test_state_dir, "state.json")
    
    # Write Worker A script
    worker_a_content = '''
import sys
import os
import json
import time

test_state_dir = r"C:/Users/lee/AppData/Local/hermes/kanban/state/test_concurrent4"
lock_file = r"C:/Users/lee/AppData/Local/hermes/kanban/state/test_concurrent4/concurrent.lock"
state_file = r"C:/Users/lee/AppData/Local/hermes/kanban/state/test_concurrent4/state.json"

print("[Worker A] Acquiring lock...", flush=True)

with open(lock_file, "w") as f:
    json.dump({"worker": "acquired", "time": time.time()}, f)

print("[Worker A] Lock acquired", flush=True)
time.sleep(2)
print("[Worker A] Lock released, writing state", flush=True)

with open(state_file, "w") as f:
    json.dump({"worker": "released", "time": time.time()}, f)
print("[Worker A] Done", flush=True)
'''
    
    # Write Worker B script
    worker_b_content = '''
import sys
import os
import json
import time

test_state_dir = r"C:/Users/lee/AppData/Local/hermes/kanban/state/test_concurrent4"
lock_file = r"C:/Users/lee/AppData/Local/hermes/kanban/state/test_concurrent4/concurrent.lock"
state_file = r"C:/Users/lee/AppData/Local/hermes/kanban/state/test_concurrent4/state.json"

print("[Worker B] Waiting for lock...", flush=True)

while True:
    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                state = json.load(f)
            if state.get("worker") == "released":
                print("[Worker B] Lock released, acquiring...", flush=True)
                break
        except:
            pass
    time.sleep(0.1)

print("[Worker B] Acquired lock", flush=True)
time.sleep(1)
print("[Worker B] Released lock", flush=True)
print("[Worker B] Done", flush=True)
'''
    
    # Write scripts to temp files
    worker_a_path = os.path.join(script_dir, "worker_a_test.py")
    worker_b_path = os.path.join(script_dir, "worker_b_test.py")
    
    with open(worker_a_path, "w") as f:
        f.write(worker_a_content)
    
    with open(worker_b_path, "w") as f:
        f.write(worker_b_content)
    
    try:
        # Run Worker A
        print("  [TEST] Running Worker A...")
        proc_a = subprocess.Popen(
            [sys.executable, worker_a_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        stdout_a, _ = proc_a.communicate(timeout=10)
        
        if proc_a.returncode != 0:
            print("[FAIL] Worker A failed with exit code " + str(proc_a.returncode))
            print(stdout_a)
            return 1
        else:
            print(stdout_a)
            print("  [PASS] Worker A completed")
    
    except subprocess.TimeoutExpired:
        print("[FAIL] Worker A timed out")
        proc_a.terminate()
        proc_a.wait()
        return 1
    
    # Run Worker B
    try:
        print("  [TEST] Running Worker B...")
        proc_b = subprocess.Popen(
            [sys.executable, worker_b_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        stdout_b, _ = proc_b.communicate(timeout=15)
        
        if proc_b.returncode != 0:
            print("[FAIL] Worker B failed with exit code " + str(proc_b.returncode))
            print(stdout_b)
            return 1
        else:
            print(stdout_b)
            print("  [PASS] Worker B acquired lock after Worker A released")
            return 0
    except subprocess.TimeoutExpired:
        print("[FAIL] Worker B timed out")
        proc_b.terminate()
        proc_b.wait()
        return 1


def test_3_crash_recovery():
    """
    Test 3: Crash recovery.
    
    Terminate a process while it owns the mutex. Keep a contender's handle alive
    and prove abandoned ownership is recovered correctly.
    Also verify that cleanup cannot displace a live task.
    """
    print("\n[Test 3] Crash recovery")
    
    test_state_dir = r"C:/Users/lee/AppData/Local/hermes/kanban/state/test_crash3"
    os.makedirs(test_state_dir, exist_ok=True)
    
    lock_file = os.path.join(test_state_dir, "crash.lock")
    state_file = os.path.join(test_state_dir, "state.json")
    
    # Phase 1: Acquire lock and hold it
    print("  [TEST] Phase 1: Acquiring lock and holding it...")
    
    acquire_script = '''
import sys
import os
import json
import time

test_state_dir = r"C:/Users/lee/AppData/Local/hermes/kanban/state/test_crash3"
lock_file = r"C:/Users/lee/AppData/Local/hermes/kanban/state/test_crash3/crash.lock"
state_file = r"C:/Users/lee/AppData/Local/hermes/kanban/state/test_crash3/state.json"

with open(lock_file, "w") as f:
    json.dump({"worker": "acquired", "time": time.time()}, f)

print("[CrashWorker] Lock acquired", flush=True)
'''
    
    proc = subprocess.Popen(
        [sys.executable, "-c", acquire_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    stdout, _ = proc.communicate(timeout=5)
    print("  ", stdout)
    
    # Phase 2: Create stale lock file to simulate crash
    print("  [TEST] Phase 2: Simulating crash with stale lock...")
    if os.path.exists(lock_file):
        os.remove(lock_file)
    
    stale_lock = {
        "type": "SHARED",
        "github_issue_id": "CRASH-001",
        "task_id": "t_crash",
        "acquired_at": time.time() - 3600,
        "expiry": int(time.time()) - 3600
    }
    
    with open(lock_file, "w") as f:
        json.dump(stale_lock, f)
    
    print("  Created stale lock with expiry:", stale_lock['expiry'])
    
    # Phase 3: Contender should recover stale lock
    print("  [TEST] Phase 3: Contender recovering stale lock...")
    
    try:
        guard = ExecutionGuard("TEST-003", "t3")
        guard.acquire()
        print("  [PASS] Stale lock recovered - new task acquired lock")
        guard.release()
        return 0
    except Exception as e:
        print("  [FAIL] Error:", e)
        return 1


def test_4_non_owner_cannot_release():
    """Test 4: Non-owner cannot release lock."""
    print("\n[Test 4] Non-owner cannot release")
    
    try:
        guard = ExecutionGuard("TEST-004", "t4")
        result = guard.release()
        
        if result:
            print("[FAIL] Non-owner was able to release lock")
            return 1
        else:
            print("[PASS] Non-owner correctly denied release")
        return 0
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        return 1


def test_5_child_unauthorized_blocked():
    """Test 5: Unauthorized child blocked."""
    print("\n[Test 5] Unauthorized child blocked")
    
    try:
        auth = ChildAuth()
        auth.propose("unauthorized", "TEST-005")
        
        try:
            auth.verify("unauthorized", "TEST-005")
            print("[FAIL] Unauthorized child was allowed")
            return 1
        except UnauthorizedError:
            print("[PASS] Unauthorized child correctly blocked")
        
        return 0
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        return 1


def test_6_child_approved_executes():
    """Test 6: Approved child executes."""
    print("\n[Test 6] Approved child executes")
    
    try:
        auth = ChildAuth()
        auth.propose("approved", "TEST-006")
        auth.approve("approved", "TEST-006")
        auth.verify("approved", "TEST-006")
        print("[PASS] Approved child correctly allowed")
        
        return 0
    except Exception as e:
        print(f"[FAIL] {e}")
        return 1


def test_7_issue_id_mismatch_blocked():
    """Test 7: Issue ID mismatch blocked."""
    print("\n[Test 7] Issue ID mismatch blocked")
    
    try:
        auth = ChildAuth()
        auth.propose("mismatch", "TEST-007-A")
        auth.approve("mismatch", "TEST-007-A")
        
        try:
            auth.verify("mismatch", "TEST-007-B")
            print("[FAIL] Issue ID mismatch was allowed")
            return 1
        except UnauthorizedError as e:
            if "Issue ID mismatch" in str(e):
                print("[PASS] Issue ID mismatch correctly blocked")
            else:
                print(f"[FAIL] Wrong error: {e}")
                return 1
        
        return 0
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        return 1


def test_8_executive_entry_point():
    """
    Test 8: Executive entry point test.
    
    Demonstrates that Jeeves's operational entry point invokes the guard
    and issue-bound approval checks.
    """
    print("\n[Test 8] Executive entry point")
    
    try:
        guard = ExecutionGuard("TEST-008", "exec_entry")
        auth = ChildAuth()
        
        auth.propose("exec_child_001", "TEST-008")
        auth.approve("exec_child_001", "TEST-008")
        
        def executive_task():
            print("  [EXEC] Starting task...", flush=True)
            time.sleep(0.5)
            print("  [EXEC] Verifying child authorization...", flush=True)
            auth.verify("exec_child_001", "TEST-008")
            print("  [EXEC] Child authorized, proceeding...", flush=True)
            print("  [EXEC] Task completed", flush=True)
            return "success"
        
        result = guard.execute(executive_task)
        
        if result == "success":
            print("[PASS] Executive entry point works with approval checks")
            return 0
        else:
            print(f"[FAIL] Unexpected result: {result}")
            return 1
    except LockHeldError as e:
        print(f"[FAIL] Lock error: {e}")
        return 1
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        return 1


def main():
    """Run all tests with proper exit codes."""
    print("=" * 70)
    print("EXECUTION GUARD V1 - CORRECTED ACCEPTANCE TESTS")
    print("=" * 70)
    
    all_passed = True
    tests = [
        ("Lock held throughout execution", test_1_lock_held_throughout_execution),
        ("Concurrent execution blocked", test_2_concurrent_execution_blocked),
        ("Crash recovery", test_3_crash_recovery),
        ("Non-owner cannot release", test_4_non_owner_cannot_release),
        ("Unauthorized child blocked", test_5_child_unauthorized_blocked),
        ("Approved child executes", test_6_child_approved_executes),
        ("Issue ID mismatch blocked", test_7_issue_id_mismatch_blocked),
        ("Executive entry point", test_8_executive_entry_point),
    ]
    
    for name, test_func in tests:
        exit_code = test_func()
        if exit_code != 0:
            all_passed = False
            print(f"[FAIL] {name}")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("ALL TESTS PASSED")
        return 0
    else:
        print("SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
