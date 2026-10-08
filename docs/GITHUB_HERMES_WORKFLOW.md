# GitHub-to-Hermes workflow

> October 8 update: See [Jeeves project discovery and human completion](JEEVES_PROJECT_DISCOVERY_AND_ACCEPTANCE.md) for the current dynamic selector and accepted-completion path. The Project #3/#4 selector and separate manual issue-closure steps below describe the prior release.

Current operating checkpoint: October 7, 2026, after PRs #28/#29 and Issue #30 acceptance. This replaces earlier foreground-only procedures for ordinary project work.

## Authority

Lee controls scope, priorities, Execution Order, Sprint, acceptance, issue closure, merges and deployment. ChatGPT helps plan, implement authorized support work and review. Jeeves/Hermes executes the selected task scope and returns evidence. The explicitly selected GitHub project is the authoritative backlog and decision record; native Kanban records local task/run state. The existing launcher supports nvrenuf's LandmarkSignal Project #3 and Hermes Optimization Project #4 on the same LandmarkSignal board.

## Actual workflow

| Stage/action | Implemented behavior |
|---|---|
| GitHub Queued for Jeeves | Selects open issues for the explicit import batch. It is a Project Status option, not a label. |
| Import queued work | Lee clicks the button in Jeeves Launch. It reads GitHub and creates unassigned native Triage cards with preserved source requirements, identities, hashes and recorded blockers. |
| Triage / To-do | Hermes specifies/decomposes work according to native orchestration settings. GitHub blockers are source facts; the importer does not itself create dependency cards or native links. |
| Ready | Native dispatch eligibility. It can launch work automatically; To-do can auto-promote when prerequisites finish. There is no separate implemented manual approval stop before dispatch. |
| Running | Ordinary native tools are available for the task scope under existing Hermes approvals and configured limits. |
| Review | Workers call `kanban_request_review`. Default/Jeeves hooks block `kanban_complete` on the LandmarkSignal board. Automatic review dispatch is disabled. |
| Complete | Lee accepts the actual output through the dashboard. This completes the local card, not its GitHub issue. |
| Send results to GitHub Human Review / Blocked | Explicit button reads actual task/run/profile/workspace and artifact hashes, posts deduplicated evidence and changes only the existing Project Status. It leaves the issue open. |
| GitHub Done / issue closure | Separate human acceptance of the full issue requirements. Project #3's Done-to-close workflow makes premature Done consequential. |

Queue/import authorizes planning, not all subsequent execution. The operator must understand that native preparation can reach Ready and start workers. A card title, assignment or model claim does not prove human approval. The lack of an enforced planning-only dispatch gate remains an open Issue #9 requirement; documentation does not supply it.

## Operator procedure

1. Select a bounded GitHub issue and clear requirements; preserve human-controlled fields.
2. Set its Project Status to Queued for Jeeves. Review the whole queue before importing, because the button imports all eligible queued issues.
3. Open [Jeeves Launch](http://127.0.0.1:9119/jeeves-launch?profile=jeeves), select **Source GitHub project**, confirm the visible active source, and click Import queued work. Only queued, open issues from that project are imported. Inspect created/existing/skipped results. Project #3 remains the initial selection for compatibility.
4. Follow the card on the [LandmarkSignal Kanban](http://127.0.0.1:9119/kanban?profile=jeeves). Ready can dispatch; this is not a holding column.
5. Inspect real files in the card's assigned workspace at Review. A fresh chat may start in another directory; read the card's `workspace_path` instead of guessing.
6. Request scoped corrections as needed. Accept with Complete only when satisfied.
7. In Jeeves Launch, select the originating project. Under Hermes → GitHub review, click Refresh results, inspect the correct issue's evidence, then explicitly send it to GitHub. Results are filtered by source; return checks the card, snapshot, live issue and exact originating project item before any write. Changing the selector never retargets a result. The selector is locked while an import or return is pending.
8. Close the GitHub issue only after all its criteria are accepted. Completed subtasks do not establish completion of their root issue.

## Identity, repeats and evidence

The importer uses a stable Project/issue key, not a body hash, to prevent duplicates. Changed issue text does not silently reset an existing task. Archived linked cards are reported as existing and never reactivated by intake. Request a separately scoped follow-up for unfinished work rather than deleting history to force another import.

Project #3 retains its historical `github-project3:<project-id>:<issue-id>` keys and workspace paths, including legacy URL-bound pilot cards. Other approved sources use `github-project:<project-id>:<issue-id>`. An issue deliberately selected in two projects has a separate identity in each; imports never rebind one project's card to another project's item. Source JSON preserves original requirements, body hash, update time, repository/issue IDs, project/item IDs, dependencies, Priority, Execution Order and Sprint. None of those planning fields or execution authorization values are updated by return.

## Approving another source project

Add a source only after Lee explicitly approves it. Using the existing authenticated `gh` client, verify the user owner, project number and node ID. Add that tuple and its display title to [github_projects.py](../github_projects.py). Do not accept arbitrary browser-supplied IDs or create another launcher, board, profile or bot. The catalog endpoint and selector use this same allowlist.

Verify the existing Status field has `Queued for Jeeves`, `Human Review` and `Blocked`. Preserve its field ID, existing option IDs and item values; do not create a duplicate field. [configure_project4_status.py](../configure_project4_status.py) is intentionally pinned to Project #4 and is not a generic project mutator. Add project-specific tests for queue isolation, preserved identities, archived idempotency and return mismatch rejection; refresh the focused asset manifest and use the focused installer below.

## Focused launcher installation and rollback

[setup_github_projects.ps1](../setup_github_projects.ps1) runs the targeted fixture suite, installs only the five files in [github_projects_assets.json](../github_projects_assets.json), and verifies installed hashes/imports and read-only project connections as normal Lee. It tries normal-user maintenance first; only a protected-file failure requests a scoped administrator helper. Existing file/directory protections remain intact and any new helper grants normal Lee read/execute. It does not read or edit configuration, change the native runtime, import cards or dispatch work. The historical installers remain historical payloads; do not rerun them for this update.

The installer checks the reviewed old/new hashes and refuses unknown edits. Each changed file is backed up under `landmarksignal-v1/recovery/github-projects-<id>` with `paths.json`; partial writes roll back. Elevated maintenance separately retains original file/directory ACLs under `github-projects-acls-<id>`. For rollback, first verify the standalone dashboard is idle, compare installed hashes with `paths.json`, restore each recorded `.before` file to its listed path and remove only the newly introduced helper where its backup is null. Preserve/restore recorded ACLs and reload the same standalone dashboard. Do not restore a board database or older configuration.

[reload_github_projects_dashboard.ps1](../reload_github_projects_dashboard.ps1) is a separate explicit step. It verifies the port 9119 process, owner and ancestry, refuses administrator execution or active work, then reloads only that standalone dashboard as Lee. Hermes Desktop, gateways, model servers and infrastructure are outside this operation. Review the live selector and both sources without importing a queue or posting synthetic evidence; a real-item mutation check needs a separately approved bounded item.

Evidence includes actual native task/run/profile/workspace and current local artifact hashes. It is not automatic publication of file contents, a remote PR, proof of passing tests or a verified human approval record. Return supports Human Review and Blocked; continuous synchronization of every native state is not implemented.

## Limits and precedence

See [checkpoint](HERMES_WORKFLOW_CHECKPOINT.md) for live evidence and remaining Issue #9 criteria. Ready/To-do approval enforcement and a live failed/Blocked return remain unresolved. Global cross-profile mutex enforcement, ordinary child authorization, startup recovery, scheduled/unattended work and additional model/bot deployments are not established by this checkpoint.

Follow current explicit Lee decisions, the current operating model/contract, this workflow and execution policy. Dated reports, old skill references and earlier no-tools document launchers describe their own historical routes; they do not override this current workflow. A documentation change does not install updated instructions in the local Hermes skill folder.
