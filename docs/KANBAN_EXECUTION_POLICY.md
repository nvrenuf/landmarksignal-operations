# LandmarkSignal Kanban Execution Policy

## Board and ownership

Use the existing `landmarksignal` board at `%LOCALAPPDATA%\hermes\kanban\boards\landmarksignal\kanban.db`. Do not initialize another board or database. GitHub Project #3 remains the authoritative backlog and priority record.

## Approval and lifecycle

Follow [GitHub to Hermes workflow](GITHUB_HERMES_WORKFLOW.md). Import/prepare, specification drafting, execution, child work and acceptance are distinct permissions. A GitHub field or native state never replaces exact task/scope approval.

Native To-do can automatically become Ready. Native Specify uses an auxiliary model and invokes this promotion path. Native Scheduled is a time wait, not human approval. Until a guarded reusable intake/specification route exists, do not use those paths to launch new work. Existing document entries use verified sticky Blocked holds until manual release.

## Current enforcement

- Canonical implementation: `execution_guard_v1_final.py`, Windows mutex `LandmarkSignalV1Mutex`. Fail closed if native mutex support is unavailable; no weaker fallback. Hold ownership through agent close. Diagnostic timestamp expiry never displaces a live owner.
- Installed `landmarksignal-execution` pre-tool policy blocks unowned shell, task mutation and delegation; planning reads remain available. It does not prove guard coverage for every native dashboard/API/auxiliary path.
- Gateway dispatch and automatic review dispatch remain off. Manual orchestration disables automatic decomposition only. Do not enable unattended/cron dispatch, swarm or ordinary dispatch to implement intake.
- Maximum one participating guarded execution; no discretionary concurrency override in the accepted implementation. Cross-session enforcement and same-user tamper resistance are not established.
- Child creation and execution require applicable separate scoped Lee approval. The two document routes expose no tools or children.

## Approved procedure

Use the Jeeves Launch tab for reviewed document contracts. The runner checks binding, scope snapshot, existing work and approval before exact claim. Successful output/evidence returns to Review; Lee accepts and completes the card. Failed runs remain for review with no automatic retry. Returning to Review is authorized as part of that run.

Keep original run evidence immutable; store review corrections and human acceptance separately. Preserve unrelated cards and all GitHub Priority, Execution Order, Sprint and authorization values. A completed subtask is not approval to close its GitHub issue.

Legacy `kanban-control.py`, `kanban-guard.bat`, separate acquire/release commands and older safety reports are not operating instructions. Do not use a short-lived CLI lock around a dispatcher that starts longer-lived workers.
