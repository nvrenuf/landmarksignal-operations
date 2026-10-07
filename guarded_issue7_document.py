"""One manual foreground Jeeves documentation task; no dispatcher or child."""

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
if __name__ == "__main__":
    root = Path(os.environ["LOCALAPPDATA"]) / "hermes"
    os.environ["HERMES_HOME"] = str(root / "profiles/jeeves")
    os.environ["HERMES_PROFILE"] = "jeeves"
    sys.path.insert(0, str(root / "hermes-agent"))
    import hermes_bootstrap  # noqa: F401

from execution_guard_v1_final import ExecutionGuard, _atomic_json
from install_jeeves_policy import bootstrap, verify_installed
from landmarksignal_policy import SCOPE_MODULE

TASK_ID = "t_0b33c85e"
TASK_KEY = "landmarksignal-issue7-status-mapping-v1"
ISSUE_URL = "https://github.com/nvrenuf/landmarksignal-operations/issues/7"
STAGES = ["Idea", "Defined", "Sprint Ready", "Queued for Jeeves", "In Progress",
          "Validation", "Human Review", "Blocked", "Done"]


def snapshot(conn):
    return {r["id"]: dict(r) for r in conn.execute("SELECT * FROM tasks")}


def make_agent():
    from hermes_cli.config import load_config
    from hermes_cli.runtime_provider import resolve_runtime_provider
    from hermes_constants import resolve_reasoning_config
    from run_agent import AIAgent
    cfg = load_config()
    model = cfg.get("model", {}).get("default")
    if model != "Qwen3.5-9B-Q4_K_M" or cfg.get("model", {}).get("provider") not in {"local", "llamacpp", "custom"}:
        raise RuntimeError("Existing Jeeves local-model configuration differs")
    if cfg.get("kanban", {}).get("review_dispatch") is not False:
        raise RuntimeError("Automatic review dispatch must remain disabled")
    runtime = resolve_runtime_provider(target_model=model)
    route = urlparse(runtime.get("base_url", ""))
    if route.scheme != "http" or route.hostname not in {"127.0.0.1", "localhost"} or route.port != 18434:
        raise RuntimeError("Expected local model route is unavailable; no remote call made")
    agent = AIAgent(
        model=model, api_key=runtime.get("api_key"), base_url=runtime.get("base_url"),
        provider=runtime.get("provider"), requested_provider=runtime.get("requested_provider"),
        api_mode=runtime.get("api_mode"), max_iterations=3, run_budget_seconds=120,
        enabled_toolsets=[], disabled_toolsets=["all"], quiet_mode=True,
        skip_context_files=True, skip_memory=True, skip_background_review=True,
        fallback_model=None, reasoning_config=resolve_reasoning_config(cfg, model),
        ephemeral_system_prompt=("You are Jeeves drafting documentation for " + ISSUE_URL
                                 + ". No tools, children, infrastructure access or completion authority."
                                 + " Return the Markdown document only, without code fences."),
    )
    if agent.tools:
        agent.close()
        raise RuntimeError("Unexpected tools exposed; no model call made")
    return agent, model


def main():
    if not sys.stdin.isatty():
        raise RuntimeError("Run from Lee's interactive PowerShell")
    root, _, profile = bootstrap()
    verify_installed(profile)
    board = root / "kanban/boards/landmarksignal/kanban.db"
    workspace = root / "landmarksignal-v1/work/issue7-status-mapping"
    document = workspace / "KANBAN_STATUS_MAPPING.md"
    evidence_path = workspace / "evidence.json"
    if not board.is_file():
        raise RuntimeError("Existing board is missing")
    if document.exists() or evidence_path.exists():
        raise RuntimeError("Existing deliverable/evidence requires review; no overwrite or replay")
    with closing(sqlite3.connect(board, timeout=10)) as conn:
        conn.row_factory = sqlite3.Row
        original = snapshot(conn)
        row = original.get(TASK_ID)
        if (not row or row.get("idempotency_key") != TASK_KEY or row["status"] != "blocked"
                or ISSUE_URL not in (row.get("body") or "")
                or row.get("workspace_kind") != "dir"
                or Path(row.get("workspace_path") or "").resolve() != workspace.resolve()
                or row.get("assignee") is not None or row.get("claim_lock") or row.get("worker_pid")):
            raise RuntimeError("Exact parked card/binding/workspace differs; nothing released")
        if any(r["status"] == "running" for r in original.values()):
            raise RuntimeError("An existing card is running; nothing released")
        original.pop(TASK_ID)
        print("Issue:", ISSUE_URL)
        print("Task:", TASK_ID)
        print("Output:", document)
        print("One foreground Jeeves document draft; no tools, children, commits or infrastructure access")
        if input("Type APPROVE ISSUE 7 to run this document task: ").strip() != "APPROVE ISSUE 7":
            raise RuntimeError("Execution not approved")
        guard = ExecutionGuard("7", TASK_ID, timeout=0)
        results = {"issue_url": ISSUE_URL, "kanban_task_id": TASK_ID, "profile": "jeeves",
                   "human_approval": True, "execution_mode": "foreground_no_tools_document",
                   "started_at": datetime.now(timezone.utc).isoformat(),
                   "task_body_sha256": hashlib.sha256(row["body"].encode()).hexdigest()}

        def execute():
            from hermes_cli import kanban_db as kb
            from hermes_cli import kanban_db_dispatch as kbd
            task = None
            try:
                if any(r["status"] == "running" for r in snapshot(conn).values()):
                    raise RuntimeError("Another card began running; nothing released")
                if not kb.unblock_task(conn, TASK_ID):
                    raise RuntimeError("Exact manual hold could not be released")
                task = kb.claim_task(conn, TASK_ID, ttl_seconds=900)
                if task is None or task.id != TASK_ID or ISSUE_URL not in (task.body or ""):
                    raise RuntimeError("Exact card was not claimed; no model call made")
                results["kanban_run_id"] = task.current_run_id
                kbd._set_worker_pid(conn, TASK_ID, os.getpid())
                sys.modules[SCOPE_MODULE] = SimpleNamespace(
                    guard=guard, issue_url=ISSUE_URL, workspace=workspace, acceptance=True)
                print("RUNNING: Jeeves is drafting the document (120-second model-run budget)", flush=True)
                agent, model = make_agent()
                try:
                    prompt = task.body + "\n\nReviewed facts for the draft:\n" + (
                        "Produce a concise Markdown document, at most 900 words. Include a nine-row mapping table in the given order. "
                        "Do not invent native states or commands. Idea/Defined/Sprint Ready are GitHub planning stages, not dispatch authority. "
                        "Hermes triage is specification intake; todo waits for dependencies or assignment; ready is eligible waiting work; "
                        "running means claimed work; review is human-review handoff; blocked waits for intervention; scheduled waits for time; "
                        "done follows human acceptance; archived preserves inactive records. "
                        "Validation is checks/evidence, not a renamed native state. "
                        "Manual orchestration disables automatic decomposition only, not worker dispatch. "
                        "A native manual hold requires a blocked event as well as blocked status. "
                        "The approved foreground route owns a Windows mutex through its actual agent lifetime and cleanup. "
                        "The first draft is this one local Jeeves no-tools run; no persistent worker or child is deployed. "
                        "Detached dashboard dispatch, full automatic GitHub handoff, old-session policy activation and startup recovery remain unverified. "
                        "Project statuses do not enforce permissions. Include exact issue URL, task/run IDs, scoped workspace, approved deliverable, "
                        "separate child approval when applicable, evidence/artifact handoff, and Lee's human review before completion/merge. "
                        "Explicitly label intended rules versus verified foreground behavior. No instructions to nudge a dispatcher or bypass a guard."
                    )
                    reply = agent.run_conversation(prompt)
                    content = (reply.get("final_response") or "").strip()
                    if not reply.get("completed") or len(content) < 300 or any(stage not in content for stage in STAGES):
                        raise RuntimeError("Draft incomplete or missing required stages; no document published")
                    results.update(model=model, api_calls=reply.get("api_calls"), tools_exposed=0)
                finally:
                    agent.close()
                if any(snapshot(conn).get(k) != v for k, v in original.items()):
                    raise RuntimeError("An original card changed; stop for review")
                workspace.mkdir(parents=True, exist_ok=True)
                with document.open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(content + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                results.update(status="AWAITING_HUMAN_REVIEW", original_cards_preserved=True,
                               document=str(document), document_sha256=hashlib.sha256((content + "\n").encode()).hexdigest(),
                               scope_held_through_agent_close=True,
                               completed_at=datetime.now(timezone.utc).isoformat())
                _atomic_json(evidence_path, results)
                ok, reason = kb.request_review(
                    conn, TASK_ID, expected_run_id=task.current_run_id, with_reason=True,
                    summary="Issue #7 status mapping draft produced by guarded foreground Jeeves; Lee review required.",
                    metadata={"github_issue_url": ISSUE_URL, "artifacts": [str(document), str(evidence_path)]})
                if not ok or kb.get_task(conn, TASK_ID).status != "review":
                    raise RuntimeError("Review handoff failed: " + str(reason))
                results["kanban_status"] = "review"
                _atomic_json(evidence_path, results)
            except BaseException as error:
                results.update(status="INCOMPLETE", error_type=type(error).__name__)
                results.pop("kanban_status", None)
                _atomic_json(evidence_path, results)
                latest = kb.get_task(conn, TASK_ID)
                if latest and (latest.status == "ready" or (task and latest.status == "running" and latest.current_run_id == task.current_run_id)):
                    kb.block_task(conn, TASK_ID, kind="needs_input", expected_run_id=task.current_run_id if task else None,
                                  reason="Issue #7 document run incomplete; manual review required")
                print("Incomplete evidence:", evidence_path)
                raise
            finally:
                sys.modules.pop(SCOPE_MODULE, None)

        guard.execute(execute)
        print("PASS: useful document drafted by actual Jeeves and handed to Review")
        print("Document:", document)
        print("Evidence:", evidence_path)
        print("No child, detached dispatch, GitHub completion, commit or merge performed")


if __name__ == "__main__":
    main()
