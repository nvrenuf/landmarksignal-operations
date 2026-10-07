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

from document_tasks import get_spec, digest as spec_digest, task_body, find_card

SPEC = get_spec("issue6-roster")
TASK_ID = None
TASK_KEY = SPEC["key"]
ISSUE_URL = SPEC["issue_url"]
STAGES = SPEC["markers"]


def snapshot(conn):
    return {r["id"]: dict(r) for r in conn.execute("SELECT * FROM tasks")}


def make_agent():
    from hermes_cli.config import load_config
    from hermes_cli.runtime_provider import resolve_runtime_provider
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
        api_mode=runtime.get("api_mode"), max_iterations=1, run_budget_seconds=120,
        max_tokens=1800,
        enabled_toolsets=[], disabled_toolsets=["all"], quiet_mode=True,
        skip_context_files=True, skip_memory=True, skip_background_review=True,
        fallback_model=None, reasoning_config={"enabled": False, "effort": "none"},
        ephemeral_system_prompt=("You are Jeeves drafting documentation for " + ISSUE_URL
                                 + ". No tools, children, infrastructure access or completion authority."
                                 + " Return the Markdown document only, without code fences."),
    )
    if agent.tools:
        agent.close()
        raise RuntimeError("Unexpected tools exposed; no model call made")
    return agent, model


def main(dashboard_approval=None):
    global TASK_ID
    if dashboard_approval is None:
        raise RuntimeError("This worker requires the guarded dashboard approval")
    if dashboard_approval is None and not sys.stdin.isatty():
        raise RuntimeError("Run from Lee's interactive PowerShell")
    root, _, profile = bootstrap()
    verify_installed(profile)
    board = root / "kanban/boards/landmarksignal/kanban.db"
    workspace = root / "landmarksignal-v1/work" / SPEC["workspace"]
    document = workspace / SPEC["filename"]
    evidence_path = workspace / "evidence.json"
    if not board.is_file():
        raise RuntimeError("Existing board is missing")
    if document.exists() or evidence_path.exists():
        raise RuntimeError("Existing deliverable/evidence requires review; no overwrite or replay")
    with closing(sqlite3.connect(board, timeout=10)) as conn:
        conn.row_factory = sqlite3.Row
        original = snapshot(conn)
        row = find_card(conn, SPEC, workspace)
        TASK_ID = row["id"]
        if dashboard_approval.get("task_id") != TASK_ID or dashboard_approval.get("contract_sha256") != spec_digest(SPEC):
            raise RuntimeError("Approval is not bound to this task and reviewed contract")
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
        if dashboard_approval is None:
            if input("Type APPROVE ISSUE 7 to run this document task: ").strip() != "APPROVE ISSUE 7":
                raise RuntimeError("Execution not approved")
        else:
            expected = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
            if dashboard_approval.get("card_sha256") != expected:
                raise RuntimeError("Card changed after dashboard approval; nothing released")
        guard = ExecutionGuard(str(SPEC["issue_number"]), TASK_ID, timeout=0)
        results = {"issue_url": ISSUE_URL, "kanban_task_id": TASK_ID, "profile": "jeeves",
                   "human_approval": True, "execution_mode": "foreground_no_tools_document",
                   "started_at": datetime.now(timezone.utc).isoformat(),
                   "task_body_sha256": hashlib.sha256(row["body"].encode()).hexdigest(),
                   "contract_sha256": spec_digest(SPEC), "document_contract": SPEC["selector"],
                   "source_issue_body_sha256": SPEC["source_issue_body_sha256"],
                   "source_updated_at": SPEC["source_updated_at"]}
        if dashboard_approval is not None:
            results["execution_mode"] = "dashboard_guarded_no_tools_document"

        def execute():
            from hermes_cli import kanban_db as kb
            from hermes_cli import kanban_db_dispatch as kbd
            task = None
            try:
                if snapshot(conn).get(TASK_ID) != row:
                    raise RuntimeError("Exact approved card changed before claim; nothing released")
                if any(r["status"] == "running" for r in snapshot(conn).values()):
                    raise RuntimeError("Another card began running; nothing released")
                if not kb.unblock_task(conn, TASK_ID):
                    raise RuntimeError("Exact manual hold could not be released")
                task = kb.claim_task(conn, TASK_ID, ttl_seconds=900)
                if task is None or task.id != TASK_ID or task.body != row["body"]:
                    raise RuntimeError("Exact card was not claimed; no model call made")
                results["kanban_run_id"] = task.current_run_id
                kbd._set_worker_pid(conn, TASK_ID, os.getpid())
                sys.modules[SCOPE_MODULE] = SimpleNamespace(
                    guard=guard, issue_url=ISSUE_URL, workspace=workspace, acceptance=True)
                print("RUNNING: Jeeves is drafting the document (120-second model-run budget)", flush=True)
                agent, model = make_agent()
                try:
                    prompt = SPEC["prompt"] + "\nIssue: " + ISSUE_URL + "; task: " + TASK_ID + "; run: " + str(task.current_run_id)
                    reply = agent.run_conversation(prompt)
                    content = (reply.get("final_response") or "").strip()
                    results.update(model=model, api_calls=reply.get("api_calls"), tools_exposed=0,
                                   generation_limits={"max_tokens": 1800, "max_iterations": 1, "reasoning_effort": "none"},
                                   model_completed=reply.get("completed"), response_characters=len(content),
                                   missing_required_markers=[stage for stage in STAGES if stage not in content])
                    if content:
                        partial = workspace / "model-response.txt"
                        with partial.open("x", encoding="utf-8") as stream:
                            stream.write(content)
                        results["model_response_path"] = str(partial)
                    if not reply.get("completed") or len(content) < 300 or any(stage not in content for stage in STAGES):
                        raise RuntimeError("Draft incomplete or missing required roles; no document published")
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
                    summary="Approved document draft produced by guarded Jeeves; Lee review required. No bots created.",
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
                                  reason="Document run incomplete; manual review required")
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
    if len(sys.argv) == 3 and sys.argv[1] == "--dashboard-approved-document":
        SPEC = get_spec(sys.argv[2])
        if "prompt" not in SPEC or "markers" not in SPEC:
            raise RuntimeError("This document contract requires its legacy worker")
        TASK_KEY = SPEC["key"]
        ISSUE_URL = SPEC["issue_url"]
        STAGES = SPEC["markers"]
        record_path = Path(os.environ["LOCALAPPDATA"]) / "hermes/landmarksignal-v1/work" / SPEC["workspace"] / "dashboard-launch.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        import hmac
        token = os.environ.pop("LANDMARKSIGNAL_DASHBOARD_APPROVAL", "")
        if not token or not hmac.compare_digest(token, record.get("token", "")) or record.get("state") != "launching":
            raise RuntimeError("No matching dashboard approval")
        record.pop("token", None)
        record.update(state="running", worker_pid=os.getpid())
        _atomic_json(record_path, record)
        try:
            main(dashboard_approval=record)
        except BaseException as error:
            record.update(state="incomplete", error_type=type(error).__name__)
            _atomic_json(record_path, record)
            raise
        else:
            record.update(state="review")
            _atomic_json(record_path, record)
    else:
        raise RuntimeError("Unsupported arguments")
