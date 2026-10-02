
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
