"""Archive the known failed document run and update only its worker; no dispatch."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
if __name__ == "__main__":
    root = Path(os.environ["LOCALAPPDATA"]) / "hermes"
    os.environ["HERMES_HOME"] = str(root / "profiles/jeeves")
    os.environ["HERMES_PROFILE"] = "jeeves"
    sys.path.insert(0, str(root / "hermes-agent"))
    import hermes_bootstrap  # noqa: F401

TASK = "t_0b33c85e"
ISSUE = "https://github.com/nvrenuf/landmarksignal-operations/issues/7"
BODY_SHA = "258350b3479fa8dc826d4de812d02c2c69f88fc9c47ed75d6eca18ef03927ed9"
OLD_RUNNER_SHA = "3c02e7bfaaf1bd98b4933a097f5800d8a4b09d5305244d0ced29ac51f339273d"


def validate_failure(card, evidence, launch):
    if (card.get("id") != TASK or card.get("status") != "blocked"
            or card.get("idempotency_key") != "landmarksignal-issue7-status-mapping-v1"
            or card.get("worker_pid") or card.get("claim_lock") or card.get("assignee") is not None
            or hashlib.sha256((card.get("body") or "").encode()).hexdigest() != BODY_SHA):
        raise RuntimeError("Exact parked Issue 7 card changed; no retry prepared")
    if (evidence.get("status") != "INCOMPLETE" or evidence.get("kanban_task_id") != TASK
            or evidence.get("kanban_run_id") != 11 or evidence.get("issue_url") != ISSUE
            or evidence.get("task_body_sha256") != BODY_SHA
            or launch.get("state") != "incomplete" or launch.get("task_id") != TASK):
        raise RuntimeError("Only the reviewed failed run 11 may be archived")


def main():
    from execution_guard_v1_final import ExecutionGuard
    from install_jeeves_policy import bootstrap, verify_installed
    root, _, profile = bootstrap()
    verify_installed(profile)
    work = root / "landmarksignal-v1/work/issue7-status-mapping"
    board = root / "kanban/boards/landmarksignal/kanban.db"
    target = root / "plugins/landmarksignal-launch/dashboard/runner/guarded_issue7_document.py"
    new_code = (Path(__file__).parent / "guarded_issue7_document.py").read_bytes()

    def prepare():
        if hashlib.sha256(target.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != OLD_RUNNER_SHA:
            raise RuntimeError("Installed worker differs from the reviewed failed version")
        if (work / "KANBAN_STATUS_MAPPING.md").exists():
            raise RuntimeError("An existing document must be reviewed; no replay prepared")
        launch = json.loads((work / "dashboard-launch.json").read_text(encoding="utf-8"))
        evidence = json.loads((work / "evidence.json").read_text(encoding="utf-8"))
        log = (work / "dashboard-worker.log").read_text(encoding="utf-8", errors="replace")
        if "Response dominated by repeated text" not in log or "Draft incomplete or missing required stages" not in log:
            raise RuntimeError("Failure differs from the reviewed repetition stop")
        with closing(sqlite3.connect(board.as_uri() + "?mode=ro", uri=True, timeout=10)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM tasks WHERE id=?", (TASK,)).fetchone()
            if row is None:
                raise RuntimeError("Existing card is missing")
            card = dict(row)
            validate_failure(card, evidence, launch)
            if (card.get("workspace_kind") != "dir"
                    or Path(card.get("workspace_path") or "").resolve() != work.resolve()
                    or conn.execute("SELECT count(*) FROM tasks WHERE status='running'").fetchone()[0]):
                raise RuntimeError("Workspace differs or an existing task is running")
            backup = root / "landmarksignal-v1/recovery" / ("issue7-run11-" + uuid.uuid4().hex)
            backup.mkdir(parents=True)
            with closing(sqlite3.connect(backup / "kanban-before-retry.db")) as saved:
                conn.backup(saved)
        shutil.copy2(target, backup / "guarded_issue7_document.before.py")
        names = ["dashboard-launch.json", "evidence.json", "dashboard-worker.log"]
        if (work / "model-response.txt").is_file():
            names.append("model-response.txt")
        for name in names:
            shutil.copy2(work / name, backup / name)
        temporary = target.with_name(".issue7-worker-" + uuid.uuid4().hex + ".tmp")
        temporary.write_bytes(new_code)
        os.replace(temporary, target)
        # Every old result is preserved; no board record, event or retry counter is edited.
        for name in names:
            (work / name).unlink()
        print("PASS: exact failed run 11 archived and document worker updated")
        print("Backup:", backup)
        print("Board records, history, configuration and execution policy unchanged")
        print("Per-run limits: 1800 output tokens, one iteration, reasoning disabled")
        print("No model call or task dispatch performed")
        print("Refresh the dashboard; approve Issue 7 there for one retry")

    ExecutionGuard("7", TASK, timeout=0).execute(prepare)


if __name__ == "__main__":
    main()
