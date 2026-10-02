"""Fail-closed Jeeves tool policy for manually owned issue execution.

The trusted foreground runner installs an in-process scope. Models cannot
create a scope through a tool. This is a workflow boundary, not isolation from
another program deliberately running as the same Windows user.
"""

import json
import os
from pathlib import Path
import re
import sys
import threading
import uuid

SCOPE_MODULE = "landmarksignal_v1_scope"
PREFIX = "LANDMARKSIGNAL_V1: "
PLANNING_READS = {"read_file", "search_files", "web_search", "web_extract"}
FILE_READS = {"read_file", "search_files"}


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
        return blocked("Execution requires Lee's manual guarded issue entry. "
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
