"""Fail-closed Jeeves tool policy for manually owned issue execution.

The trusted foreground runner installs an in-process scope. Models cannot
create a scope through a tool. This is a workflow boundary, not isolation from
another program deliberately running as the same Windows user.
"""

import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import threading
import uuid

SCOPE_MODULE = "landmarksignal_v1_scope"
PREFIX = "LANDMARKSIGNAL_V1: "
PLANNING_READS = {"read_file", "search_files", "web_search", "web_extract",
                  "kanban_list", "kanban_show", "kanban_attachments"}
FILE_READS = {"read_file", "search_files"}


def owns_native_block(args):
    """Allow reporting a blocker, never claiming or approving execution.

    Environment labels alone are insufficient. Match the live task/run and
    worker PID against the existing board through a read-only connection.
    Hermes's own handler additionally checks its run lifecycle ownership.
    """
    if not isinstance(args, dict) or args.get("board") not in (None, "landmarksignal"):
        return False
    if args.get("kind") != "needs_input" or not isinstance(args.get("reason"), str):
        return False
    if not args["reason"].strip():
        return False
    try:
        root = Path(os.environ["LOCALAPPDATA"]) / "hermes"
        database = root / "kanban/boards/landmarksignal/kanban.db"
        task_id = os.environ["HERMES_KANBAN_TASK"]
        run_id = int(os.environ["HERMES_KANBAN_RUN_ID"])
        claim = os.environ["HERMES_KANBAN_CLAIM_LOCK"]
        if not claim or args.get("task_id", task_id) != task_id:
            return False
        if os.environ.get("HERMES_PROFILE") != "jeeves":
            return False
        if Path(os.environ["HERMES_HOME"]).resolve() != (root / "profiles/jeeves").resolve():
            return False
        if Path(os.environ["HERMES_KANBAN_DB"]).resolve() != database.resolve():
            return False
        connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
        try:
            connection.execute("PRAGMA query_only=ON")
            row = connection.execute(
                "SELECT t.status, t.assignee, t.current_run_id, t.claim_lock, t.worker_pid, "
                "r.task_id, r.status, r.profile, r.claim_lock FROM tasks t "
                "JOIN task_runs r ON r.id=t.current_run_id WHERE t.id=?", (task_id,),
            ).fetchone()
            return row == ("running", "jeeves", run_id, claim, os.getpid(),
                           task_id, "running", "jeeves", claim)
        finally:
            connection.close()
    except (KeyError, ValueError, OSError, sqlite3.Error):
        return False


def blocked(message):
    return {"action": "block", "message": PREFIX + message}


def owned_scope():
    scope = sys.modules.get(SCOPE_MODULE)
    guard = getattr(scope, "guard", None)
    owner = getattr(guard, "_owner", None)
    if (scope is None or not getattr(guard, "_acquired", False)
            or getattr(guard, "_mutex", None) is None
            or not isinstance(owner, tuple) or len(owner) != 2
            or owner[0] != os.getpid() or not isinstance(owner[1], threading.Thread)
            or not owner[1].is_alive()):
        return None
    issue_url = getattr(scope, "issue_url", "")
    match = re.fullmatch(
        r"https://github\.com/nvrenuf/landmarksignal-operations/issues/([1-9][0-9]*)",
        issue_url,
    )
    if match is None or guard.github_issue_id != match.group(1):
        return None
    return scope


def inside_workspace(scope, value):
    if not isinstance(value, str) or not value or "\x00" in value:
        return False
    root = Path(scope.workspace).resolve()
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    try:
        path.resolve().relative_to(root)
        return True
    except (OSError, ValueError):
        return False


def decide(tool_name="", args=None, **kwargs):
    """Policy runs on Hermes hook threads; it observes but never releases ownership."""
    scope = owned_scope()
    if scope is None:
        if tool_name in PLANNING_READS:
            return None
        if tool_name == "kanban_block" and owns_native_block(args):
            return None
        return blocked("Execution requires Lee's manual guarded issue entry. "
                       "Card reads are allowed. An assigned native Jeeves worker may report its own "
                       "blocker with kanban_block(kind='needs_input'). "
                       "Propose the work and await approval; do not use another tool to bypass this gate.")
    if getattr(scope, "acceptance", False):
        return blocked("Issue #19 acceptance model calls have no tool permission. "
                       "Child approval and execution are controlled by the human runner.")
    if tool_name in {"delegate_task", "kanban_create", "kanban_link", "kanban_unblock",
                     "kanban_complete", "kanban_request_review", "kanban_request_changes"}:
        return blocked("Task/child transitions belong to the issue-bound human runner.")
    if tool_name not in FILE_READS | {"write_file"}:
        return blocked("This foreground entry permits workspace file work only. "
                       "Shell, detached workers and remote delegation require a separately verified supervisor.")
    args = args if isinstance(args, dict) else {}
    if not inside_workspace(scope, args.get("path")):
        return blocked("File path must remain inside the approved issue workspace.")
    if tool_name in FILE_READS:
        return None
    from tools.approval import _yolo_active
    from tools.approval_context import _get_approval_mode
    if _yolo_active() or _get_approval_mode() != "manual":
        return blocked("Approval bypass is incompatible with guarded issue execution.")
    return {
        "action": "approve",
        "rule_key": "landmarksignal:" + uuid.uuid4().hex,
        "message": "Lee must approve this file change for " + scope.issue_url
                   + ": " + json.dumps(args, ensure_ascii=True),
    }
