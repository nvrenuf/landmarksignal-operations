"""Manual, foreground Issue #19 acceptance through the installed Jeeves API.

No dispatch CLI, one-shot approval bypass, Spark access, shell tool or product
work is permitted. A console human authorizes the parent and then the child.
The canonical Windows guard owns the entire task and both agent lifetimes.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
from types import SimpleNamespace
from urllib.parse import urlparse
import uuid

from execution_guard_v1_final import (
    ChildAuth, ExecutionGuard, UnauthorizedError, _atomic_json,
)
from install_jeeves_policy import bootstrap, verify_installed
from landmarksignal_policy import SCOPE_MODULE

ISSUE_URL = "https://github.com/nvrenuf/landmarksignal-operations/issues/19"
PR_URL = "https://github.com/nvrenuf/landmarksignal-operations/pull/20"
TASK_KEY = "landmarksignal-issue19-manual-v1"


def approve(phrase):
    if not sys.stdin.isatty():
        raise UnauthorizedError("Manual acceptance must run in Lee's interactive PowerShell")
    print("\nType exactly '" + phrase + "' to authorize this step. Anything else denies it.")
    if input("> ").strip() != phrase:
        raise UnauthorizedError("Human did not approve this step")


def task_snapshot(path):
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=3) as conn:
        conn.row_factory = sqlite3.Row
        return {row["id"]: dict(row) for row in conn.execute("SELECT * FROM tasks")}


def guard_contender(guard):
    code = (
        "import sys; from execution_guard_v1_final import ExecutionGuard,LockHeldError; "
        "g=ExecutionGuard('19','contender',timeout=0)\n"
        "try:\n g.acquire()\nexcept LockHeldError:\n sys.exit(0)\n"
        "else:\n g.release(); sys.exit(1)\n"
    )
    result = subprocess.run([sys.executable, "-c", code],
                            cwd=str(Path(__file__).resolve().parent), timeout=15,
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("A real competing process was not blocked by the owned guard")
    if not guard._acquired or guard._owner != (os.getpid(), threading.current_thread()):
        raise RuntimeError("Foreground execution ownership was lost")


def make_agent():
    from hermes_cli.config import load_config
    from hermes_cli.runtime_provider import resolve_runtime_provider
    from hermes_constants import resolve_reasoning_config
    from run_agent import AIAgent
    cfg = load_config()
    model_cfg = cfg.get("model", {})
    if not isinstance(model_cfg, dict) or model_cfg.get("provider") not in {"local", "llamacpp", "custom"}:
        raise RuntimeError("Jeeves is not configured for the reviewed local provider")
    model = model_cfg.get("default")
    if model != "Qwen3.5-9B-Q4_K_M":
        raise RuntimeError("Jeeves model changed; review the acceptance route before proceeding")
    runtime = resolve_runtime_provider(target_model=model)
    route = urlparse(runtime.get("base_url", ""))
    if route.scheme != "http" or route.hostname not in {"127.0.0.1", "localhost"} or route.port != 18434:
        raise RuntimeError("Acceptance requires the existing laptop model at loopback port 18434; no remote call made")
    agent = AIAgent(
        model=model, api_key=runtime.get("api_key"), base_url=runtime.get("base_url"),
        provider=runtime.get("provider"), requested_provider=runtime.get("requested_provider"),
        api_mode=runtime.get("api_mode"), max_iterations=3, run_budget_seconds=120,
        enabled_toolsets=[], disabled_toolsets=["all"], quiet_mode=True,
        skip_context_files=True, skip_memory=True, skip_background_review=True,
        fallback_model=None, reasoning_config=resolve_reasoning_config(cfg, model),
        ephemeral_system_prompt=("Harmless acceptance for " + ISSUE_URL
                                 + ". No tools, infrastructure access, task dispatch or completion permission."),
    )
    if agent.tools:
        agent.close()
        raise RuntimeError("Native agent unexpectedly exposes tools; acceptance stopped before the model call")
    return agent, model


def model_reply(guard, label, results):
    guard_contender(guard)
    marker = "JEEVES_ISSUE_19_" + label + "_OK"
    agent, model = make_agent()
    try:
        result = agent.run_conversation("For " + ISSUE_URL + ", reply exactly " + marker)
        if not result.get("completed") or (result.get("final_response") or "").strip() != marker:
            raise RuntimeError("Jeeves " + label.lower() + " reply did not match the acceptance marker")
        results[label.lower() + "_model_call"] = {
            "passed": True, "model": model, "marker": marker,
            "api_calls": result.get("api_calls"), "tools_exposed": 0,
        }
    finally:
        # No scope may be released until the actual agent is closed.
        agent.close()
    guard_contender(guard)


def update_guard_task_id(guard, task_id):
    path = Path(guard._lock_file)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("token") != guard._token or data.get("github_issue_id") != "19":
        raise RuntimeError("Guard metadata ownership mismatch")
    guard.task_id = task_id
    data["task_id"] = task_id
    _atomic_json(path, data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retry-blocked", action="store_true",
                        help="Explicitly retry this runner's existing blocked Issue #19 card")
    args = parser.parse_args()
    if not sys.stdin.isatty():
        raise UnauthorizedError("Run this file directly from interactive PowerShell")
    root, _, profile = bootstrap()
    verify_installed(profile)
    from hermes_cli.config import load_config
    from hermes_cli.plugins import get_pre_tool_call_block_message
    cfg = load_config()
    if cfg.get("kanban", {}).get("review_dispatch") is not False:
        raise RuntimeError("Automatic review dispatch must be disabled")
    if cfg.get("kanban", {}).get("default_assignee"):
        raise RuntimeError("A default Kanban assignee could compete with manual acceptance")
    path = root / "kanban/boards/landmarksignal/kanban.db"
    if not path.is_file():
        raise RuntimeError("Existing LandmarkSignal board database is missing")
    original = task_snapshot(path)
    if any(row.get("status") == "running" for row in original.values()):
        raise RuntimeError("An existing LandmarkSignal card is running; no work started")
    matches = [row for row in original.values()
               if row.get("idempotency_key") == TASK_KEY and row.get("status") != "archived"]
    retry_task = None
    if matches:
        if (len(matches) != 1 or not args.retry_blocked or matches[0].get("status") != "blocked"
                or ISSUE_URL not in (matches[0].get("body") or "")):
            raise RuntimeError("Acceptance card exists. Review it; only its blocked state permits an explicit --retry-blocked")
        retry_task = matches[0]["id"]
        original.pop(retry_task)
    elif args.retry_blocked:
        raise RuntimeError("No existing blocked acceptance card to retry")
    source = json.loads((Path(__file__).parent / "acceptance_issue_19.json").read_text(encoding="utf-8"))
    if source.get("number") != 19 or source.get("html_url") != ISSUE_URL or source.get("state") != "open":
        raise RuntimeError("Reviewed issue snapshot is not the authorized open Issue #19")
    print("Issue:", ISSUE_URL)
    print("Scope: local-model parent/child markers and safety evidence only")
    print("No Spark access, shell tools, product work, merge or issue completion")
    print("Retries the exact blocked test card" if retry_task else
          "Creates one explicitly bound test card on the existing LandmarkSignal board")
    print("Existing cards, GitHub issues and their fields remain unchanged")
    approve("APPROVE ISSUE 19")
    run_id = uuid.uuid4().hex
    workspace = root / "landmarksignal-v1/acceptance" / run_id
    results = {"parent_human_approval": True, "issue_url": ISSUE_URL, "review_pr_url": PR_URL,
               "source_updated_at": source.get("updated_at"),
               "source_body_sha256": hashlib.sha256(source["body"].encode()).hexdigest(),
               "started_at": datetime.now(timezone.utc).isoformat()}
    guard = ExecutionGuard("19", "acceptance-" + run_id, timeout=0)
    new_task = None

    def execute():
        nonlocal new_task
        from hermes_cli import kanban_db as kb
        from hermes_cli import kanban_db_dispatch as kbd
        workspace.mkdir(parents=True)
        # Plain connection to the existing schema: never initialize/migrate the board.
        with sqlite3.connect(path, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            if any(row["status"] == "running" for row in conn.execute("SELECT status FROM tasks")):
                raise RuntimeError("Another card began running; no model call made")
            if retry_task:
                new_task = retry_task
                if not kb.unblock_task(conn, new_task):
                    raise RuntimeError("Exact blocked test card could not be unblocked")
            else:
                new_task = kb.create_task(
                    conn, title="Issue #19: Manual guarded execution acceptance",
                    body=ISSUE_URL + "\n\n" + source["body"], assignee=None,
                    created_by="Lee (manual console approval)", workspace_kind="dir",
                    workspace_path=str(workspace), initial_status="blocked", board="landmarksignal",
                    project_id="", idempotency_key=TASK_KEY, max_runtime_seconds=300, max_retries=1,
                )
            task = None
            try:
                # This Hermes revision accepts only running/blocked at creation.
                # Release this exact new card after the manual approval above;
                # never create an automatically eligible card as a side effect.
                if not retry_task and not kb.unblock_task(conn, new_task):
                    raise RuntimeError("Exact new blocked test card could not be released")
                task = kb.claim_task(conn, new_task, ttl_seconds=900)
                if task is None or task.id != new_task or ISSUE_URL not in (task.body or ""):
                    raise RuntimeError("Exact issue-bound test card was not claimed; no model call made")
                kbd._set_worker_pid(conn, new_task, os.getpid())
                update_guard_task_id(guard, new_task)
                results["kanban_task_id"] = new_task
                results["kanban_run_id"] = task.current_run_id
                results["exact_issue_binding"] = True
                scope = SimpleNamespace(guard=guard, issue_url=ISSUE_URL,
                                        workspace=workspace, acceptance=True)
                sys.modules[SCOPE_MODULE] = scope
                for tool in ("delegate_task", "terminal", "write_file", "kanban_create"):
                    message = get_pre_tool_call_block_message(tool, {"path": str(workspace / "test.txt")})
                    if not isinstance(message, str) or not message.startswith("LANDMARKSIGNAL_V1: "):
                        raise RuntimeError("Native policy failed to deny acceptance tool: " + tool)
                results["native_policy_blocks_acceptance_tools"] = True
                model_reply(guard, "PARENT", results)
                child_id = "issue19-child-" + run_id
                auth = ChildAuth(state_dir=root / "landmarksignal-v1/private" / run_id)
                auth.propose(child_id, "19")
                callback_calls = []

                def child_callback():
                    callback_calls.append(True)
                    model_reply(guard, "CHILD", results)

                try:
                    auth.execute(child_id, "19", child_callback, guard=guard)
                except UnauthorizedError:
                    if callback_calls:
                        raise RuntimeError("Unapproved child reached the callback")
                    results["unapproved_child_blocked_before_callback"] = True
                else:
                    raise RuntimeError("Unapproved child was allowed")
                approve("APPROVE CHILD ISSUE 19")
                auth.approve(child_id, "19")
                try:
                    auth.execute(child_id, "18", child_callback, guard=guard)
                except UnauthorizedError:
                    if callback_calls:
                        raise RuntimeError("Mismatched issue reached the callback")
                    results["wrong_issue_blocked_before_callback"] = True
                else:
                    raise RuntimeError("Mismatched issue was allowed")
                auth.execute(child_id, "19", child_callback, guard=guard)
                if len(callback_calls) != 1:
                    raise RuntimeError("Approved child callback count differs from one")
                results["child_human_approval"] = True
                results["scope_held_through_parent_and_child_close"] = True
                current = task_snapshot(path)
                if any(current.get(tid) != row for tid, row in original.items()):
                    raise RuntimeError("An original card changed during acceptance")
                results["original_cards_preserved"] = True
                results["completed_at"] = datetime.now(timezone.utc).isoformat()
                results["status"] = "AWAITING_HUMAN_REVIEW"
                results["kanban_status"] = "review"
                evidence = workspace / "evidence.json"
                _atomic_json(evidence, results)
                ok, reason = kb.request_review(
                    conn, new_task, expected_run_id=task.current_run_id, with_reason=True,
                    summary="Manual Issue #19 foreground acceptance passed. Lee's review is required; do not auto-complete.",
                    metadata={"github_issue_url": ISSUE_URL, "review_pr_url": PR_URL,
                              "artifacts": [str(evidence)]},
                )
                if not ok:
                    raise RuntimeError("Human-review transition failed: " + str(reason))
                latest = kb.get_task(conn, new_task)
                if latest.status != "review":
                    raise RuntimeError("Test card did not remain in review")
                results["kanban_status"] = "review"
                _atomic_json(evidence, results)
            except BaseException as error:
                results["status"] = "INCOMPLETE"
                results.pop("kanban_status", None)
                results["error_type"] = type(error).__name__
                _atomic_json(workspace / "evidence.json", results)
                latest = kb.get_task(conn, new_task)
                # Never interfere with a claimant that won the exact-card race.
                if latest and (latest.status == "ready" or (
                        task is not None and latest.status == "running"
                        and latest.current_run_id == task.current_run_id)):
                    kb.block_task(conn, new_task, kind="needs_input",
                                  expected_run_id=task.current_run_id if task else None,
                                  reason="Manual acceptance incomplete; human review required (" + type(error).__name__ + ")")
                print("Incomplete acceptance evidence:", workspace / "evidence.json")
                raise
            finally:
                sys.modules.pop(SCOPE_MODULE, None)

    guard.execute(execute)
    current = task_snapshot(path)
    if any(current.get(tid) != row for tid, row in original.items()):
        raise RuntimeError("Original-card preservation failed after the handoff")
    print("\nPASS: guarded parent uses the actual Jeeves local model")
    print("PASS: unapproved and wrong-issue children never reach their callbacks")
    print("PASS: human-approved child uses the actual Jeeves local model")
    print("PASS: competing processes blocked; ownership spans both actual agent lifetimes")
    print("PASS: original Kanban cards preserved; test card awaits human review")
    print("Test card:", new_task)
    print("Evidence:", workspace / "evidence.json")
    print("Review PR:", PR_URL)
    print("Issue #19 remains open; no GitHub status/authorization values were changed")
    print("Acceptance exit code: 0")


if __name__ == "__main__":
    main()
