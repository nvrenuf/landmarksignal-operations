"""Reviewed document-only contracts; the browser cannot supply execution instructions."""
import hashlib
import json
from pathlib import Path

SPECS = {
    "issue7-status-mapping": {
        "issue_number": 7, "key": "landmarksignal-issue7-status-mapping-v1",
        "task_id": "t_0b33c85e", "workspace": "issue7-status-mapping",
        "filename": "KANBAN_STATUS_MAPPING.md", "title": "Status mapping document",
    },
    "issue6-roster": {
        "issue_number": 6, "key": "landmarksignal-issue6-roster-document-v1",
        "task_id": None, "workspace": "issue6-roster",
        "filename": "BOT_ROSTER_DRAFT.md", "title": "Planned bot roster draft",
        "source_issue_body_sha256": "c641e610c88c359f0287d76a0e7b428084a76e648a94d9a06ead0c0e1f00aec8",
        "source_updated_at": "2026-10-01T05:16:40Z",
        "markers": ["Argus", "LMS-Coder", "LMS-Security", "LMS-Reviewer", "LMS-Research"],
        "prompt": (
            "Write BOT_ROSTER_DRAFT.md, 250-400 words. Return only Markdown. "
            "This is a proposed roster, not a deployment report. All five workers are PLANNED, "
            "not created or validated. One table with exactly five rows: name, responsibility, "
            "boundary, approval requirement. Argus is the proposed LandmarkSignal domain lead; "
            "LMS-Coder drafts approved code changes; LMS-Security reviews security risks; "
            "LMS-Reviewer independently checks deliverables; LMS-Research researches approved topics. "
            "Jeeves coordinates approved tasks; Lee and ChatGPT choose priorities. "
            "For every row say what requires separate human approval. No worker approves itself, "
            "deploys, merges, starts children, changes credentials, or accesses infrastructure "
            "without explicit scoped approval. State that profiles, credentials, allowed tools and "
            "workspaces must be configured and validated before deployment. Current task: one "
            "document only, no tools or children, no bot creation, no child/card creation, no "
            "configuration changes. Return draft for Lee's review; do not complete the GitHub issue. "
            "Do not invent commands or claim bots are active. Stop after the document."
        ),
    },
}


def get_spec(key):
    if key not in SPECS:
        raise RuntimeError("Task is not a reviewed document contract")
    spec = dict(SPECS[key])
    spec["selector"] = key
    spec["issue_url"] = "https://github.com/nvrenuf/landmarksignal-operations/issues/" + str(spec["issue_number"])
    spec["approval_phrase"] = "APPROVE ISSUE " + str(spec["issue_number"])
    return spec


def digest(spec):
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


def task_body(spec):
    return (spec["issue_url"] + "\n\nDOCUMENT-ONLY APPROVED SCOPE\n" + spec["prompt"]
            + "\n\nContract SHA256: " + digest(spec)
            + "\nManual dashboard release only. Native blocked hold until Lee approves. "
            "No ordinary dispatcher launch. One local model call with no tools or children. "
            "Return artifact and run evidence to Review; Lee accepts before Done. "
            "This subtask does not complete all requirements of Issue #6.")


def find_card(conn, spec, work):
    rows = list(conn.execute("SELECT * FROM tasks WHERE idempotency_key=? AND status!='archived'", (spec["key"],)))
    if len(rows) != 1:
        raise RuntimeError("Expected exactly one prepared document card")
    card = dict(rows[0])
    if (spec.get("task_id") and card["id"] != spec["task_id"]
            or spec["issue_url"] not in (card.get("body") or "")
            or card.get("workspace_kind") != "dir"
            or Path(card.get("workspace_path") or "").resolve() != work.resolve()):
        raise RuntimeError("Document card binding differs")
    if spec["selector"] != "issue7-status-mapping" and card.get("body") != task_body(spec):
        raise RuntimeError("Document instructions differ from the reviewed contract")
    return card
