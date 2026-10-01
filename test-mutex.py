#!/usr/bin/env python3
"""
Test Named Mutex functionality for cross-process protection.
"""

import os
import sys

# Add repo to path
repo_path = "/c/Users/lee/landmarksignal-operations"
sys.path.insert(0, repo_path)

try:
    import win32event
    HAS_WIN32EVENT = True
    print("[INFO] win32event available - can create Named Mutexes")
except ImportError:
    HAS_WIN32EVENT = False
    print("[INFO] win32event NOT available - will use multiprocessing Lock as fallback")

try:
    import multiprocessing.synchronize
    HAS_MULTIPROCESSING = True
except ImportError:
    HAS_MULTIPROCESSING = False

from execution_guard import GlobalExecutionGuard, NamedMutexWrapper

print("=" * 60)
print("NAMED MUTEX FUNCTIONALITY TEST")
print("=" * 60)

# Test 1: Check mutex wrapper
print("\nTest 1: NamedMutexWrapper creation")
mutex = NamedMutexWrapper("TestMutex_001")
if mutex is not None:
    print("[PASS] Mutex wrapper created")
else:
    print("[FAIL] Mutex wrapper failed")

# Test 2: Acquire and release mutex
print("\nTest 2: Mutex acquire/release")
if mutex.acquire(timeout=1.0):
    print("[PASS] Mutex acquired")
    mutex.release()
    print("[PASS] Mutex released")
else:
    print("[FAIL] Failed to acquire mutex")

# Test 3: Check GlobalExecutionGuard has mutex
print("\nTest 3: GlobalExecutionGuard initialization")
guard = GlobalExecutionGuard()
if hasattr(guard, '_mutex'):
    print("[PASS] Guard has mutex attribute")
else:
    print("[FAIL] Guard missing mutex attribute")

# Test 4: Status check
print("\nTest 4: Guard status (no lock)")
status = guard.get_status()
if not status.get('has_shared_lock', False):
    print("[PASS] Status shows released")
else:
    print(f"[FAIL] Unexpected status: {status}")

# Test 5: Acquire lock
print("\nTest 5: Acquire lock")
if guard.acquire("TEST-001", "t_test_001"):
    print("[PASS] Lock acquired")
else:
    print("[FAIL] Failed to acquire lock")

# Test 6: Verify lock held
print("\nTest 6: Verify lock held")
status = guard.get_status()
if status.get('has_shared_lock', False):
    print("[PASS] Lock is held")
else:
    print("[FAIL] Lock not held")

# Test 7: Release lock
print("\nTest 7: Release lock")
if guard.release("TEST-001", "t_test_001"):
    print("[PASS] Lock released")
else:
    print("[FAIL] Failed to release lock")

# Test 8: Verify released
print("\nTest 8: Verify released")
status = guard.get_status()
if not status.get('has_shared_lock', False):
    print("[PASS] Lock is released")
else:
    print(f"[FAIL] Lock still held: {status}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)

# Cleanup
guard = GlobalExecutionGuard()
guard.release("TEST-001", "t_test_001")
print("[CLEANUP] Locks released")
