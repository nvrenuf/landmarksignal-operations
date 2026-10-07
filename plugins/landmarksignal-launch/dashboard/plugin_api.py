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
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "runner"))
from document_tasks import SPECS, get_spec, digest as spec_digest, find_card

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()
TASK = "t_0b33c85e"
KEY = "landmarksignal-issue7-status-mapping-v1"
ISSUE = "https://github.com/nvrenuf/landmarksignal-operations/issues/7"


def paths(key="issue7-status-mapping"):
    if os.name != "nt":
        raise HTTPException(409, "This integration requires the native Windows runtime")
    root = Path(os.environ["LOCALAPPDATA"]) / "hermes"
    work = root / "landmarksignal-v1/work" / get_spec(key)["workspace"]
    return root, work, root / "kanban/boards/landmarksignal/kanban.db"


def require_jeeves(request):
    from hermes_cli.config import get_hermes_home
    root, _, _ = paths()
    if request.query_params.get("profile") != "jeeves" or Path(get_hermes_home()).resolve() != (root / "profiles/jeeves").resolve():
        raise HTTPException(403, "Select the Jeeves profile")


def inspect_card(key="issue7-status-mapping"):
    spec = get_spec(key)
    root, work, board = paths() if key == "issue7-status-mapping" else paths(key)
    if not board.is_file():
        raise HTTPException(409, "Existing LandmarkSignal board is missing")
    with closing(sqlite3.connect(board.as_uri() + "?mode=ro", uri=True, timeout=5)) as conn:
        conn.row_factory = sqlite3.Row
        try:
            card = find_card(conn, spec, work)
        except RuntimeError as error:
            raise HTTPException(409, str(error))
        running = conn.execute("SELECT count(*) FROM tasks WHERE status='running'").fetchone()[0]
    ready = (card["status"] == "blocked" and not running
             and card.get("assignee") is None and not card.get("worker_pid") and not card.get("claim_lock")
             and not (work / "dashboard-launch.json").exists()
             and not (work / spec["filename"]).exists()
             and not (work / "evidence.json").exists())
    return card, ready, hashlib.sha256(json.dumps(card, sort_keys=True).encode()).hexdigest()


def selection(request):
    key = getattr(request, "query_params", {}).get("task", "issue7-status-mapping")
    try:
        get_spec(key)
    except RuntimeError as error:
        raise HTTPException(409, str(error))
    return key


@router.get("/tasks")
def tasks(request: Request):
    require_jeeves(request)
    return {"tasks": [{"selector": key, "title": get_spec(key)["title"], "issue_number": get_spec(key)["issue_number"]}
                       for key in SPECS]}


@router.get("/status")
def status(request: Request):
    require_jeeves(request)
    key = selection(request)
    spec = get_spec(key)
    card, ready, digest = inspect_card(key)
    _, work, _ = paths() if key == "issue7-status-mapping" else paths(key)
    record = {}
    if (work / "dashboard-launch.json").is_file():
        record = json.loads((work / "dashboard-launch.json").read_text(encoding="utf-8"))
    evidence = {}
    if (work / "evidence.json").is_file():
        evidence = json.loads((work / "evidence.json").read_text(encoding="utf-8"))
    return {"task_id": card["id"], "issue_url": spec["issue_url"], "title": spec["title"],
            "scope": card["body"], "filename": spec["filename"], "approval_phrase": spec["approval_phrase"], "contract_sha256": spec_digest(spec), "card_status": card["status"], "can_launch": ready,
            "card_sha256": digest, "launch_state": record.get("state", "not_started"),
            "evidence_status": evidence.get("status"), "error_type": record.get("error_type", evidence.get("error_type")),
            "document_available": (work / spec["filename"]).is_file(), "workspace": str(work)}


class Approval(BaseModel):
    phrase: str
    card_sha256: str
    contract_sha256: str = ""


@router.post("/start")
@router.post("/issue7/start")
def start(request: Request, approval: Approval):
    require_jeeves(request)
    # A browser launch must originate at this authenticated dashboard, not another site.
    if request.headers.get("origin") != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Launch from this dashboard page")
    key = selection(request)
    spec = get_spec(key)
    if str(getattr(getattr(request, "url", None), "path", "")).endswith("/issue7/start") and key != "issue7-status-mapping":
        raise HTTPException(409, "Legacy endpoint only accepts Issue 7")
    card, ready, digest = inspect_card(key)
    if key != "issue7-status-mapping" and not secrets.compare_digest(approval.contract_sha256, spec_digest(spec)):
        raise HTTPException(409, "Document contract changed")
    if approval.phrase != spec["approval_phrase"] or not secrets.compare_digest(approval.card_sha256, digest):
        raise HTTPException(409, "Approval or card snapshot differs; refresh and review")
    if not ready:
        raise HTTPException(409, "Card is not parked, another task runs, or this launch already exists")
    root, work, _ = paths() if key == "issue7-status-mapping" else paths(key)
    python = root / "hermes-agent/venv/Scripts/python.exe"
    runner = Path(__file__).resolve().parent / "runner" / ("guarded_issue7_document.py" if key == "issue7-status-mapping" else "guarded_document_task.py")
    arguments = ["--dashboard-approved-issue7"] if key == "issue7-status-mapping" else ["--dashboard-approved-document", key]
    if not python.is_file() or not runner.is_file():
        raise HTTPException(409, "Installed worker files are missing")
    work.mkdir(parents=True, exist_ok=True)
    record_path = work / "dashboard-launch.json"
    token = secrets.token_urlsafe(32)
    record = {"state": "launching", "card_sha256": digest, "token": token,
              "started_at": datetime.now(timezone.utc).isoformat(), "task_id": card["id"],
              "selector": key, "contract_sha256": spec_digest(spec)}
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
            subprocess.Popen([str(python), "-B", str(runner), *arguments],
                             cwd=str(runner.parent), env=env, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as error:
        record.pop("token", None)
        record.update(state="incomplete", error_type=type(error).__name__)
        record_path.write_text(json.dumps(record), encoding="utf-8")
        raise HTTPException(500, "Worker could not start; recorded for manual review")
    return {"started": True, "task_id": card["id"]}


@router.get("/document")
def document(request: Request):
    require_jeeves(request)
    key = selection(request)
    spec = get_spec(key)
    _, work, _ = paths() if key == "issue7-status-mapping" else paths(key)
    target = work / spec["filename"]
    if not target.is_file():
        raise HTTPException(404, "Document is not available yet")
    return {"filename": target.name, "markdown": target.read_text(encoding="utf-8")}


@router.post('/github-intake')
def github_intake(request: Request):
    require_jeeves(request)
    if request.headers.get('origin') != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Import from this dashboard page')
    from github_queue_intake import run_intake
    root, _, _ = paths()
    try:
        return run_intake(root)
    except Exception as error:
        # Never return provider/CLI errors containing keys. Expected refusal text is local.
        if isinstance(error, RuntimeError):
            raise HTTPException(409, str(error))
        raise HTTPException(409, 'Intake stopped: ' + type(error).__name__ + '. No automatic retry.')
