# LandmarkSignal Kanban execution policy

## Existing board

Use `landmarksignal` at `%LOCALAPPDATA%\hermes\kanban\boards\landmarksignal\kanban.db`. Do not create a replacement board or treat the root `kanban.db` as this board. GitHub Project #3 remains the authoritative backlog and human-controlled field record.

## Implemented controls

- Ordinary default/Jeeves native project tools are available. The installed `landmarksignal-execution` hook blocks LandmarkSignal worker `kanban_complete` and directs it to `kanban_request_review`; dashboard Complete remains a human action.
- Both profiles configure `review_dispatch=false`, `max_in_progress=1`, `max_in_progress_per_profile=1` and `max_spawn=1`. Existing model and native approval settings were preserved. Configuration and hooks are not proof of universal cross-profile exclusion or OS tamper resistance.
- Ready can dispatch; To-do can auto-promote. Manual orchestration and `dispatch_in_gateway=false` do not establish that every possible native launch path is disabled.
- Explicit foreground acceptance calls remain tool-free. `execution_guard_v1_final.py` and the Windows `LandmarkSignalV1Mutex` protect participating foreground routes and serialize integration control actions. They do not universally guard ordinary detached workers.
- Batch intake creates Triage cards, preserves existing records and backs up the board. Repeats, including archived linked cards, do not reset or relaunch existing work.
- Explicit result return sets only Human Review or Blocked, posts deduplicated evidence, verifies remote Status and leaves the GitHub issue open.

## Outstanding requirement

Planning-only intake does not grant execution permission, but an enforced approval stop before automatic dispatch is not installed. The record-level approval helper is a utility, not a dispatcher interceptor. This is an open Issue #9 criterion, alongside a live failed/Blocked-result return. Do not claim an unapproved Ready card is guaranteed to stay idle.

Ordinary child execution authorization, unattended/scheduled operations and runtime recovery require their own scope and evidence. Do not extrapolate from a no-tools acceptance test.

## Acceptance and cleanup

Workers stop at Review; Lee inspects artifacts and accepts through Complete. Native Done is not GitHub acceptance. Close a GitHub issue only after explicit acceptance of its full criteria.

The October 7 clean-board operation archived 16 inspected cards in one backed-up transaction without changing workspace files, existing history, dependency links or GitHub. Archived is retention, not completion of unresolved GitHub requirements. Native Archive can also clean workspaces and recompute readiness; do not assume future archival is harmless to files or dependent work.

Legacy separate acquire/release commands, `kanban-control.py`, `kanban-guard.bat` and old repair scripts are historical; they are not the current operator entry. See [workflow](GITHUB_HERMES_WORKFLOW.md) and [folder map](HERMES_FOLDER_MAP.md).
