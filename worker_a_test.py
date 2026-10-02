
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
