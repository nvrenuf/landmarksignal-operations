# GitHub-to-Hermes workflow

Current operating checkpoint: October 7, 2026, after PRs #28/#29 and Issue #30 acceptance. This replaces earlier foreground-only procedures for ordinary project work.

## Authority

Lee controls scope, priorities, Execution Order, Sprint, acceptance, issue closure, merges and deployment. ChatGPT helps plan, implement authorized support work and review. Jeeves/Hermes executes the selected task scope and returns evidence. GitHub Project #3 is the authoritative backlog and decision record; native Kanban records local task/run state.

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
3. Open [Jeeves Launch](http://127.0.0.1:9119/jeeves-launch?profile=jeeves) and click Import queued work. Inspect created/existing/skipped results.
4. Follow the card on the [LandmarkSignal Kanban](http://127.0.0.1:9119/kanban?profile=jeeves). Ready can dispatch; this is not a holding column.
5. Inspect real files in the card's assigned workspace at Review. A fresh chat may start in another directory; read the card's `workspace_path` instead of guessing.
6. Request scoped corrections as needed. Accept with Complete only when satisfied.
7. In Jeeves Launch, under Hermes → GitHub review, click Refresh results, inspect the correct issue's evidence, then explicitly send it to GitHub.
8. Close the GitHub issue only after all its criteria are accepted. Completed subtasks do not establish completion of their root issue.

## Identity, repeats and evidence

The importer uses a stable Project/issue key, not a body hash, to prevent duplicates. Changed issue text does not silently reset an existing task. Archived linked cards are reported as existing and never reactivated by intake. Request a separately scoped follow-up for unfinished work rather than deleting history to force another import.

Evidence includes actual native task/run/profile/workspace and current local artifact hashes. It is not automatic publication of file contents, a remote PR, proof of passing tests or a verified human approval record. Return supports Human Review and Blocked; continuous synchronization of every native state is not implemented.

## Limits and precedence

See [checkpoint](HERMES_WORKFLOW_CHECKPOINT.md) for live evidence and remaining Issue #9 criteria. Ready/To-do approval enforcement and a live failed/Blocked return remain unresolved. Global cross-profile mutex enforcement, ordinary child authorization, startup recovery, scheduled/unattended work and additional model/bot deployments are not established by this checkpoint.

Follow current explicit Lee decisions, the current operating model/contract, this workflow and execution policy. Dated reports, old skill references and earlier no-tools document launchers describe their own historical routes; they do not override this current workflow. A documentation change does not install updated instructions in the local Hermes skill folder.
