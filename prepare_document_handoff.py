"""Back up, upgrade the existing document launcher and park one exact card. No execution."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
if __name__ == "__main__":
    root = Path(os.environ["LOCALAPPDATA"]) / "hermes"
    os.environ["HERMES_HOME"] = str(root / "profiles/jeeves")
    os.environ["HERMES_PROFILE"] = "jeeves"
    sys.path.insert(0, str(root / "hermes-agent"))
    import hermes_bootstrap  # noqa: F401

from document_tasks import get_spec, task_body, find_card


def normalized_hash(value):
    return hashlib.sha256(value.replace(b"\r\n", b"\n")).hexdigest()


def stage_files(source):
    files = {}
    plugin = source / "plugins/landmarksignal-launch"
    for path in plugin.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            files[str(path.relative_to(plugin)).replace("\\", "/")] = path.read_bytes()
    for name in ("guarded_document_task.py", "document_tasks.py"):
        files["dashboard/runner/" + name] = (source / name).read_bytes()
    return files


def verify_assets(target, files, old):
    for name, expected in old.items():
        path = target / name
        if not path.is_file():
            raise RuntimeError("Reviewed installed asset missing: " + name)
        actual = normalized_hash(path.read_bytes())
        new = normalized_hash(files[name]) if name in files else expected
        if actual not in {expected, new}:
            raise RuntimeError("Installed asset differs from reviewed old/new versions: " + name)
    for name, value in files.items():
        path = target / name
        if path.exists() and name not in old and normalized_hash(path.read_bytes()) != normalized_hash(value):
            raise RuntimeError("An unexpected new asset already exists: " + name)


def prepare_card(conn, kb, spec, work):
    before = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM tasks")}
    if any(r["status"] == "running" for r in before.values()):
        raise RuntimeError("A task is already running")
    matches = [r for r in before.values() if r.get("idempotency_key") == spec["key"] and r["status"] != "archived"]
    if matches:
        card = find_card(conn, spec, work)
        if card["status"] != "blocked" or card.get("assignee") or card.get("worker_pid") or card.get("claim_lock"):
            raise RuntimeError("Existing roster card is not safely parked; no reset performed")
        if not kb._has_sticky_block(conn, card["id"]):
            raise RuntimeError("Existing card lacks a native manual hold")
        return card["id"]
    conn.execute("BEGIN IMMEDIATE")
    try:
        current = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM tasks")}
        if current != before:
            raise RuntimeError("Board changed during preparation")
        task_id = kb.create_task(
            conn, title="Issue #6: Draft planned bot responsibilities and approval boundaries",
            body=task_body(spec), initial_status="blocked", assignee=None,
            created_by="Lee-approved manual document handoff", workspace_kind="dir",
            workspace_path=str(work), project_id="", board="landmarksignal",
            idempotency_key=spec["key"], max_runtime_seconds=180, max_retries=0,
        )
        # Publish the new card and its native sticky manual event together. Never
        # expose an unheld card to recompute_ready between commits.
        conn.execute("UPDATE tasks SET block_kind='needs_input' WHERE id=?", (task_id,))
        conn.execute("INSERT INTO task_events(task_id,kind,payload,created_at) VALUES (?,?,?,?)",
                     (task_id, "blocked", json.dumps({"kind": "needs_input", "reason": "Lee must approve the exact document contract in the guarded dashboard", "source": "manual_document_handoff"}), int(time.time())))
        if not kb._has_sticky_block(conn, task_id):
            raise RuntimeError("Native manual hold was not recognized")
        after = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM tasks")}
        if set(after) != set(before) | {task_id} or any(after[k] != v for k, v in before.items()):
            raise RuntimeError("Existing card preservation failed")
        conn.commit()
        return task_id
    except BaseException:
        conn.rollback()
        raise


def main():
    from install_jeeves_policy import bootstrap, verify_installed
    from execution_guard_v1_final import ExecutionGuard
    import yaml
    root, _, profile = bootstrap()
    from hermes_cli import kanban_db as kb
    verify_installed(profile)
    source = Path(__file__).resolve().parent
    spec = get_spec("issue6-roster")
    issue = json.loads((source / "approved_document_issue6.json").read_text(encoding="utf-8-sig"))
    if (issue["html_url"] != spec["issue_url"] or issue["state"] != "open"
            or hashlib.sha256(issue["body"].encode()).hexdigest() != spec["source_issue_body_sha256"]):
        raise RuntimeError("Reviewed GitHub source differs")
    target = root / "plugins/landmarksignal-launch"
    files = stage_files(source)
    old = json.loads((source / "reviewed_dashboard_assets.json").read_text(encoding="utf-8-sig"))
    configs = [root / "config.yaml", profile / "config.yaml"]
    config_before = {str(p): p.read_bytes() for p in configs}
    for path in configs:
        cfg = yaml.safe_load(config_before[str(path)])
        plugins = cfg.get("plugins", {})
        if "landmarksignal-launch" not in plugins.get("enabled", []) or "landmarksignal-launch" in plugins.get("disabled", []):
            raise RuntimeError("Existing launch plugin is not enabled; configuration left unchanged")
    board = root / "kanban/boards/landmarksignal/kanban.db"
    if not board.is_file():
        raise RuntimeError("Existing board is missing")
    work = root / "landmarksignal-v1/work" / spec["workspace"]
    if any((work / name).exists() for name in ("dashboard-launch.json", spec["filename"], "evidence.json")):
        raise RuntimeError("This document already has a launch/result; review it, do not replay")
    recovery = root / "landmarksignal-v1/recovery" / ("document-handoff-" + uuid.uuid4().hex)

    def apply():
        verify_assets(target, files, old)
        with closing(sqlite3.connect(board, timeout=5)) as conn:
            conn.row_factory = sqlite3.Row
            if conn.execute("SELECT count(*) FROM tasks WHERE status='running'").fetchone()[0]:
                raise RuntimeError("Existing task is running")
            previous = conn.execute("SELECT status FROM tasks WHERE id='t_0b33c85e'").fetchone()
            if not previous or previous["status"] != "done":
                raise RuntimeError("Completed Issue #7 card is not Done; nothing prepared")
            for marker in (root / "landmarksignal-v1/work").glob("*/dashboard-launch.json"):
                if json.loads(marker.read_text(encoding="utf-8")).get("state") in {"launching", "running"}:
                    raise RuntimeError("A dashboard worker is still launching/running")
            recovery.mkdir(parents=True)
            with closing(sqlite3.connect(recovery / "kanban.before-handoff.db")) as backup:
                conn.backup(backup)
            work.mkdir(parents=True, exist_ok=True)
            task_id = prepare_card(conn, kb, spec, work)
        changed = []
        try:
            for name, value in files.items():
                path = target / name
                before = path.read_bytes() if path.exists() else None
                if before == value:
                    continue
                if before is not None:
                    saved = recovery / "plugin-before" / name
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    saved.write_bytes(before)
                path.parent.mkdir(parents=True, exist_ok=True)
                temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
                try:
                    temp.write_bytes(value)
                    os.replace(temp, path)
                finally:
                    if temp.exists(): temp.unlink()
                changed.append((path, before))
            if any(p.read_bytes() != config_before[str(p)] for p in configs):
                raise RuntimeError("Configuration changed concurrently")
            if any((target / name).read_bytes() != value for name, value in files.items()):
                raise RuntimeError("Installed document assets failed verification")
        except BaseException:
            for path, before in reversed(changed):
                if before is None: path.unlink()
                else: path.write_bytes(before)
            print("Plugin update rolled back. Any prepared card remains safely blocked for review.")
            raise
        (recovery / "preparation.json").write_text(json.dumps({
            "prepared_at": datetime.now(timezone.utc).isoformat(), "task_id": task_id,
            "issue_url": spec["issue_url"], "execution_authorized": False,
            "original_cards_preserved": True, "configuration_unchanged": True,
        }, indent=2), encoding="utf-8")
        print("PASS: exact Issue #6 document card prepared with native manual hold")
        print("Task ID:", task_id)
        print("PASS: completed Issue #7 and all existing cards preserved; configurations unchanged")
        print("Backup:", recovery)
        print("No model call, task claim/dispatch, bot creation or child authorization performed")
        print("Restart the browser dashboard only; then review scope and type APPROVE ISSUE 6")

    ExecutionGuard("6", "prepare-document-handoff", timeout=0).execute(apply)


if __name__ == "__main__":
    main()
