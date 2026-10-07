# LandmarkSignal Kanban Execution Policy

## Board and ownership

Use the existing `landmarksignal` board at `%LOCALAPPDATA%\hermes\kanban\boards\landmarksignal\kanban.db`. Do not initialize another board or database. GitHub Project #3 remains the authoritative backlog and priority record.

## Approval and lifecycle

Follow [GitHub to Hermes workflow](GITHUB_HERMES_WORKFLOW.md). Import/prepare, specification drafting, execution, child work and acceptance are distinct permissions. A GitHub field or native state never replaces exact task/scope approval.

Permit normal dependency-based To-do -> Ready promotion. Ready means prepared and eligible, not authorized to execute. Lee approves the exact scope at Approve and run; no automatic dispatcher may consume an unapproved Ready card. Native Specify uses an auxiliary model and invokes promotion, so its guarded planning boundary still requires verification. Native Scheduled is a time wait, not human approval. Existing document pilots used sticky Blocked holds; preserve those records without treating them as the target reusable workflow.

## Current enforcement

- Canonical implementation: `execution_guard_v1_final.py`, Windows mutex `LandmarkSignalV1Mutex`. Fail closed if native mutex support is unavailable; no weaker fallback. Hold ownership through agent close. Diagnostic timestamp expiry never displaces a live owner.
- Installed `landmarksignal-execution` pre-tool policy blocks unowned shell, task mutation and delegation; planning reads remain available. It does not prove guard coverage for every native dashboard/API/auxiliary path.
- Gateway dispatch and automatic review dispatch remain off. Manual orchestration disables automatic decomposition only. Do not enable unattended/cron dispatch, swarm or ordinary dispatch to implement intake.
- Maximum one participating guarded execution; no discretionary concurrency override in the accepted implementation. Cross-session enforcement and same-user tamper resistance are not established.
- Child creation and execution require applicable separate scoped Lee approval. The two document routes expose no tools or children.

## General Ready-card launch verification still required

Verify actual gateway/background/ordinary dispatch settings and paths, not just one profile flag. Demonstrate an unapproved Ready card remains idle, a changed/unapproved scope is denied, and only the exact approved card launches under the existing guard. Do not enable ordinary dispatch or relax the tool hook to obtain this behavior. Existing document tests do not establish this general boundary.

## Approved procedure

Use the Jeeves Launch tab for reviewed document contracts. The runner checks binding, scope snapshot, existing work and approval before exact claim. Successful output/evidence returns to Review; Lee accepts and completes the card. Failed runs remain for review with no automatic retry. Returning to Review is authorized as part of that run.

Keep original run evidence immutable; store review corrections and human acceptance separately. Preserve unrelated cards and all GitHub Priority, Execution Order, Sprint and authorization values. A completed subtask is not approval to close its GitHub issue.

Legacy `kanban-control.py`, `kanban-guard.bat`, separate acquire/release commands and older safety reports are not operating instructions. Do not use a short-lived CLI lock around a dispatcher that starts longer-lived workers.
