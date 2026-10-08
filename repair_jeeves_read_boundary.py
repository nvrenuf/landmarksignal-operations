"""Replace only the inspected Jeeves policy and its existing runner copies.

No board writes, configuration edits, model requests or task retries.
"""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import uuid

OLD_NORMALIZED_SHA = "3c90716e1a931cc8cf37fbc217694c87862ae942d71030464b46e727c0eeaf75"


def normalized(content):
    return content.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8")


def replace(path, content):
    fd, name = tempfile.mkstemp(prefix=".read-policy-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    if os.name != "nt":
        raise RuntimeError("Run this from Lee's native Windows PowerShell")
    root = Path(os.environ["LOCALAPPDATA"]) / "hermes"
    source = Path(__file__).resolve().parent
    new = (source / "landmarksignal_policy.py").read_bytes()
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
        if hashlib.sha256(normalized(original)).hexdigest() != OLD_NORMALIZED_SHA:
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
    sys.path.insert(0, str(source))
    from landmarksignal_policy import decide
    for tool in ("kanban_show", "kanban_list", "kanban_attachments"):
        if decide(tool, {"board": "landmarksignal"}) is not None:
            raise RuntimeError("Read probe failed: " + tool)
    for tool in ("terminal", "write_file", "delegate_task", "kanban_create", "kanban_complete",
                 "kanban_request_review", "kanban_unblock", "kanban_block"):
        if decide(tool, {}).get("action") != "block":
            raise RuntimeError("Unowned execution probe failed: " + tool)
    print("PASS: card reads permitted; unowned execution and completion still denied")
    print("PASS: native blocker reporting requires the exact live Jeeves task/run/claim/PID")
    print("PASS: configuration bytes preserved; board accessed read-only")
    print("Changed policy files:", len(changed))
    if originals:
        print("Backup:", backup)
    print("Existing running sessions need a runtime reload to use the new policy")
    print("No task retried, claimed, dispatched, completed or approved; no model call")
    print("Native execution authorization remains a separate unverified integration boundary")


if __name__ == "__main__":
    main()
