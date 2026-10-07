"""Authenticated dashboard launch of one pinned, issue-bound no-tools worker.

The host authenticates /api/plugin requests. No generic command or file API.
Each launch also needs an exact card snapshot and explicit approval phrase.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()
TASK = "t_0b33c85e"
KEY = "landmarksignal-issue7-status-mapping-v1"
ISSUE = "https://github.com/nvrenuf/landmarksignal-operations/issues/7"


def paths():
    if os.name != "nt":
        raise HTTPException(409, "This integration requires the native Windows runtime")
    root = Path(os.environ["LOCALAPPDATA"]) / "hermes"
    work = root / "landmarksignal-v1/work/issue7-status-mapping"
    return root, work, root / "kanban/boards/landmarksignal/kanban.db"


def require_jeeves(request):
    from hermes_cli.config import get_hermes_home
    root, _, _ = paths()
    if request.query_params.get("profile") != "jeeves" or Path(get_hermes_home()).resolve() != (root / "profiles/jeeves").resolve():
        raise HTTPException(403, "Select the Jeeves profile")


def inspect_card():
    root, work, board = paths()
    if not board.is_file():
        raise HTTPException(409, "Existing LandmarkSignal board is missing")
    with closing(sqlite3.connect(board.as_uri() + "?mode=ro", uri=True, timeout=5)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (TASK,)).fetchone()
        if row is None:
            raise HTTPException(409, "Prepared Issue 7 card is missing")
        card = dict(row)
        running = conn.execute("SELECT count(*) FROM tasks WHERE status='running'").fetchone()[0]
    if (card.get("idempotency_key") != KEY or ISSUE not in (card.get("body") or "")
            or card.get("workspace_kind") != "dir"
            or Path(card.get("workspace_path") or "").resolve() != work.resolve()):
        raise HTTPException(409, "Prepared card binding or workspace changed")
    ready = (card["status"] == "blocked" and not running
             and card.get("assignee") is None and not card.get("worker_pid") and not card.get("claim_lock")
             and not (work / "dashboard-launch.json").exists()
             and not (work / "KANBAN_STATUS_MAPPING.md").exists()
             and not (work / "evidence.json").exists())
    return card, ready, hashlib.sha256(json.dumps(card, sort_keys=True).encode()).hexdigest()


@router.get("/status")
def status(request: Request):
    require_jeeves(request)
    card, ready, digest = inspect_card()
    _, work, _ = paths()
    record = {}
    if (work / "dashboard-launch.json").is_file():
        record = json.loads((work / "dashboard-launch.json").read_text(encoding="utf-8"))
    evidence = {}
    if (work / "evidence.json").is_file():
        evidence = json.loads((work / "evidence.json").read_text(encoding="utf-8"))
    return {"task_id": TASK, "issue_url": ISSUE, "card_status": card["status"], "can_launch": ready,
            "card_sha256": digest, "launch_state": record.get("state", "not_started"),
            "evidence_status": evidence.get("status"), "error_type": record.get("error_type", evidence.get("error_type")),
            "document_available": (work / "KANBAN_STATUS_MAPPING.md").is_file(), "workspace": str(work)}


class Approval(BaseModel):
    phrase: str
    card_sha256: str


@router.post("/issue7/start")
def start(request: Request, approval: Approval):
    require_jeeves(request)
    # A browser launch must originate at this authenticated dashboard, not another site.
    if request.headers.get("origin") != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Launch from this dashboard page")
    card, ready, digest = inspect_card()
    if approval.phrase != "APPROVE ISSUE 7" or not secrets.compare_digest(approval.card_sha256, digest):
        raise HTTPException(409, "Approval or card snapshot differs; refresh and review")
    if not ready:
        raise HTTPException(409, "Card is not parked, another task runs, or this launch already exists")
    root, work, _ = paths()
    python = root / "hermes-agent/venv/Scripts/python.exe"
    runner = Path(__file__).resolve().parent / "runner/guarded_issue7_document.py"
    if not python.is_file() or not runner.is_file():
        raise HTTPException(409, "Installed worker files are missing")
    work.mkdir(parents=True, exist_ok=True)
    record_path = work / "dashboard-launch.json"
    token = secrets.token_urlsafe(32)
    record = {"state": "launching", "card_sha256": digest, "token": token,
              "started_at": datetime.now(timezone.utc).isoformat(), "task_id": TASK}
    try:
        with record_path.open("x", encoding="utf-8") as stream:
            json.dump(record, stream)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise HTTPException(409, "A launch is already recorded; no duplicate worker started")
    env = os.environ.copy()
    # No dispatcher identity is inherited by this independently guarded worker.
    for key in ("HERMES_KANBAN_TASK", "HERMES_KANBAN_CLAIM_LOCK", "HERMES_KANBAN_RUN_ID",
                "HERMES_KANBAN_WORKSPACE", "HERMES_INFERENCE_MODEL", "HERMES_INFERENCE_PROVIDER"):
        env.pop(key, None)
    env.update(LANDMARKSIGNAL_DASHBOARD_APPROVAL=token, HERMES_PROFILE="jeeves",
               HERMES_HOME=str(root / "profiles/jeeves"))
    try:
        with (work / "dashboard-worker.log").open("x", encoding="utf-8") as log:
            subprocess.Popen([str(python), "-B", str(runner), "--dashboard-approved-issue7"],
                             cwd=str(runner.parent), env=env, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as error:
        record.pop("token", None)
        record.update(state="incomplete", error_type=type(error).__name__)
        record_path.write_text(json.dumps(record), encoding="utf-8")
        raise HTTPException(500, "Worker could not start; recorded for manual review")
    return {"started": True, "task_id": TASK}


@router.get("/document")
def document(request: Request):
    require_jeeves(request)
    _, work, _ = paths()
    target = work / "KANBAN_STATUS_MAPPING.md"
    if not target.is_file():
        raise HTTPException(404, "Document is not available yet")
    return {"filename": target.name, "markdown": target.read_text(encoding="utf-8")}
