# Operating Model

## Authority

- **Lee:** final authority for priorities, sequencing, scope, approvals and acceptance.
- **ChatGPT:** planning, architecture and review advice; implements explicitly authorized support work. Cannot grant Jeeves permission on Lee's behalf.
- **GitHub Project #3:** authoritative backlog, priority, Execution Order, Sprint, dependencies, issue/PR decisions and published evidence.
- **Jeeves:** coordinates approved execution and records local task/run state in the existing LandmarkSignal Hermes board. May propose specifications or subtasks; proposals are not authorization.
- **Argus and LMS workers:** planned roles in the accepted [roster](BOT_ROSTER_DRAFT.md). Roster approval did not deploy workers or grant tool access.

## Workflow

Select a GitHub issue, prepare one Triage card, draft and review its specification, explicitly release the approved scope, execute under the guard, return evidence to Review, and complete only after Lee accepts. This is the agreed target; reusable intake and guarded specification remain pending. Native To-do may auto-promote and is not an approval gate.

See [GitHub to Hermes workflow](GITHUB_HERMES_WORKFLOW.md) for implementation boundaries, and [execution contract](JEEVES_EXECUTION_CONTRACT.md) for authority.

## Established and remaining capability

The foreground acceptance and Issue #7/#6 no-tools document routes were validated. PRs #20, #23, #24 and #25 were merged with Lee's authorization. Ordinary dispatcher supervision, general tool-enabled execution, automatic GitHub synchronization, scheduled work and startup recovery remain unverified. Do not enable them based on broad role descriptions.

Jeeves may optimize execution within the approved scope; it may not change strategy or priorities. Existing Community Capital DGX services remain production dependencies. Infrastructure work must be additive and separately authorized; do not restart, rebind or interrupt existing services.
