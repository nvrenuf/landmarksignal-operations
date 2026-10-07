"""Preserve and park the unexpectedly rewritten Issue #19 acceptance graph."""

from contextlib import closing
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

ROOT_ID = "t_a43efea7"
TASK_KEY = "landmarksignal-issue19-manual-v1"
ISSUE_URL = "https://github.com/nvrenuf/landmarksignal-operations/issues/19"


def repair(path, backup, source_body):
    with closing(sqlite3.connect(path, timeout=5, isolation_level=None)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        try:
            before = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM tasks")}
            matches = [r for r in before.values() if r.get("idempotency_key") == TASK_KEY
                       and r["status"] != "archived"]
            if len(matches) != 1 or matches[0]["id"] != ROOT_ID:
                raise RuntimeError("Expected exact acceptance card not found; nothing changed")
            root = matches[0]
            if root["status"] not in {"todo", "triage", "blocked", "ready"}:
                raise RuntimeError("Acceptance card is not in a repairable state; nothing changed")
            if root["status"] == "ready" and ISSUE_URL not in (root.get("body") or ""):
                raise RuntimeError("Ready card lacks the exact issue binding; nothing changed")
            children = set()
            for row in conn.execute("SELECT payload FROM task_events WHERE task_id=? AND kind='decomposed'", (ROOT_ID,)):
                payload = json.loads(row[0] or "{}")
                children.update(payload.get("child_ids", []))
            affected = {ROOT_ID} | children
            if not affected.issubset(before):
                raise RuntimeError("Decomposition history references a missing card; nothing changed")
            for task_id in affected:
                row = before[task_id]
                if row["status"] == "running" or row.get("claim_lock") or row.get("worker_pid"):
                    raise RuntimeError("Affected card has a worker/claim: " + task_id + "; nothing changed")
                if conn.execute("SELECT 1 FROM task_runs WHERE task_id=? AND status='running'", (task_id,)).fetchone():
                    raise RuntimeError("Affected card has a live run: " + task_id + "; nothing changed")
            external = [dict(r) for r in conn.execute("SELECT * FROM task_links")
                        if r["child_id"] == ROOT_ID and r["parent_id"] not in children]
            if external:
                raise RuntimeError("Root depends on a card outside its generated children; nothing changed")
            backup.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as reader:
                with closing(sqlite3.connect(backup)) as destination:
                    reader.backup(destination)
            now = int(time.time())

            def manual_block_event(task_id):
                # Native recompute_ready honors a newest 'blocked' event; a
                # custom audit event alone does not prevent auto-promotion.
                conn.execute("INSERT INTO task_events(task_id,kind,payload,created_at) VALUES (?,?,?,?)",
                             (task_id, "blocked", json.dumps({"kind": "needs_input", "reason": "Lee-directed manual acceptance hold; explicit console release required", "source": "manual_acceptance_recovery"}), now))

            for child in sorted(children):
                if before[child]["status"] in {"done", "archived", "review"}:
                    continue
                conn.execute("UPDATE tasks SET status='blocked', block_kind='needs_input', assignee=NULL WHERE id=?", (child,))
                conn.execute("INSERT INTO task_events(task_id,kind,payload,created_at) VALUES (?,?,?,?)",
                             (child, "manual_acceptance_parked", json.dumps({"root": ROOT_ID, "reason": "Lee-directed containment; no child execution authorized"}), now))
                manual_block_event(child)
            conn.executemany("DELETE FROM task_links WHERE parent_id=? AND child_id=?",
                             [(child, ROOT_ID) for child in children])
            conn.execute("UPDATE tasks SET title=?, body=?, assignee=NULL, status='blocked', block_kind='needs_input' WHERE id=?",
                         ("Issue #19: Manual guarded execution acceptance", ISSUE_URL + "\n\n" + source_body, ROOT_ID))
            conn.execute("INSERT INTO task_events(task_id,kind,payload,created_at) VALUES (?,?,?,?)",
                         (ROOT_ID, "manual_acceptance_repaired", json.dumps({"backup": str(backup), "parked_graph": sorted(children), "previous_status": root["status"], "reason": "Lee-directed repair of unexpected background rewrite; history and retry counters preserved"}), now))
            manual_block_event(ROOT_ID)
            after = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM tasks")}
            if set(after) != set(before) or any(after[k] != before[k] for k in before if k not in affected):
                raise RuntimeError("Unrelated card preservation check failed")
            conn.commit()
            return sorted(children)
        except BaseException:
            conn.rollback()
            raise


def main():
    from install_jeeves_policy import bootstrap, verify_installed
    from execution_guard_v1_final import ExecutionGuard
    root, _, profile = bootstrap()
    verify_installed(profile)
    source = json.loads((Path(__file__).parent / "acceptance_issue_19.json").read_text())
    if source.get("html_url") != ISSUE_URL or source.get("state") != "open":
        raise RuntimeError("Reviewed Issue #19 source differs; nothing changed")
    path = root / "kanban/boards/landmarksignal/kanban.db"
    if not path.is_file():
        raise RuntimeError("Existing board not found")
    backup = root / "landmarksignal-v1/recovery" / uuid.uuid4().hex / "kanban.before-repair.db"
    guard = ExecutionGuard("19", "manual-card-repair", timeout=0)
    children = guard.execute(lambda: repair(path, backup, source["body"]))
    from hermes_cli import kanban_db as kb
    with closing(sqlite3.connect(path)) as conn:
        conn.row_factory = sqlite3.Row
        for task_id in [ROOT_ID, *children]:
            status = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()[0]
            if status in {"done", "archived", "review"} and task_id != ROOT_ID:
                continue
            if status != "blocked" or not kb._has_sticky_block(conn, task_id):
                raise RuntimeError("Native manual-hold verification failed: " + task_id)
    print("PASS: native Hermes recognizes manual holds on parent and parked children")
    print("PASS: Issue #19 binding restored; exact card parked for manual retry")
    print("Generated child cards preserved:", ", ".join(children) or "none")
    print("Full board backup:", backup)
    print("Original unrelated cards, event history and retry counters preserved")
    print("No model call, task dispatch, child approval or process termination performed")


if __name__ == "__main__":
    main()
