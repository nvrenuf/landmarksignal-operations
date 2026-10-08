"""Replace only the inspected Jeeves policy and its existing runner copies.

No board writes, configuration edits, model requests or task retries.
"""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sqlite3
import sys
import uuid

OLD_NORMALIZED_SHA = "3c90716e1a931cc8cf37fbc217694c87862ae942d71030464b46e727c0eeaf75"


def normalized(content):
    return content.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8")


def replace(path, content):
    # tempfile retries Windows PermissionError when a directory appears writable.
    # Protected policy directories must fail immediately rather than retry names.
    temporary = path.parent / (".read-policy-" + uuid.uuid4().hex)
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main():
    if os.name != "nt":
        raise RuntimeError("Run this from Lee's native Windows PowerShell")
    root = Path(os.environ["LOCALAPPDATA"]) / "hermes"
    source = Path(__file__).resolve().parent
    new = (source / "landmarksignal_native_policy.py").read_bytes()
    compile(new, "landmarksignal_policy.py", "exec")
    profile = root / "profiles/jeeves"
    target = profile / "plugins/landmarksignal-execution/policy.py"
    candidates = [target]
    for home in (root, profile):
        candidate = home / "plugins/landmarksignal-launch/dashboard/runner/landmarksignal_policy.py"
        if candidate.is_file():
            candidates.append(candidate)
    originals = {}
    for path in candidates:
        original = path.read_bytes()  # Permission failures occur before any changes.
        if normalized(original) == normalized(new):
            continue
        if hashlib.sha256(normalized(original)).hexdigest() not in (OLD_NORMALIZED_SHA, "a7e3d1d2100a156450beec55d18bf12627d7ed1b48d75ebb418811e219d01eb3"):
            raise RuntimeError("Policy differs from the inspected version; no changes: " + str(path))
        originals[path] = original
    database = root / "kanban/boards/landmarksignal/kanban.db"
    connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True, timeout=3)
    try:
        connection.execute("PRAGMA query_only=ON")
        running = connection.execute("SELECT id FROM tasks WHERE status='running'").fetchall()
        if running:
            raise RuntimeError("Existing LandmarkSignal worker is running; no changes: " + repr(running))
    finally:
        connection.close()
    configs = {path: path.read_bytes() for path in (root / "config.yaml", profile / "config.yaml")}
    backup = root / "landmarksignal-v1/recovery" / ("read-boundary-" + uuid.uuid4().hex)
    if originals:
        backup.mkdir(parents=True)
        for index, (path, original) in enumerate(originals.items()):
            (backup / (str(index) + ".policy.before.py")).write_bytes(original)
        (backup / "paths.txt").write_text("\n".join(str(path) for path in originals), encoding="utf-8")
    changed = []
    try:
        for path in originals:
            replace(path, new)
            changed.append(path)
        for path in candidates:
            if path.read_bytes() != new and normalized(path.read_bytes()) != normalized(new):
                raise RuntimeError("Post-install verification failed: " + str(path))
        if any(path.read_bytes() != content for path, content in configs.items()):
            raise RuntimeError("Configuration changed during installation")
    except Exception:
        for path in reversed(changed):
            replace(path, originals[path])
        raise
    print("PASS: native project tools available; custom foreground-only gate removed")
    print("PASS: existing model, approvals and concurrency configuration preserved")
    print("Changed policy files:", len(changed))
    if originals:
        print("Backup:", backup)
    print("No task retried, claimed, dispatched, completed or approved; no model call")


if __name__ == "__main__":
    main()
