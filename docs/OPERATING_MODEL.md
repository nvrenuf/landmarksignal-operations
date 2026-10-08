# Operating model

## Authority

- **Lee:** final authority for scope, business priority, sequencing, acceptance, closure, merges and deployment.
- **ChatGPT:** planning and review advice, plus implementation of authorized support work. It does not grant Jeeves permission on Lee's behalf.
- **GitHub Project #3:** authoritative backlog, Priority, Execution Order, Sprint, requirements and published evidence.
- **Jeeves/Hermes workers:** carry out selected scope, record actual task/run/workspace identity, report blockers and submit outputs to Review. Default and Jeeves profiles both participate in the current native workflow; the Issue #30 worker used default.
- **Planned roster:** roles documented in [BOT_ROSTER_DRAFT.md](BOT_ROSTER_DRAFT.md). Roster acceptance does not mean those bots were deployed.

## Current operation

Lee selects a GitHub queue batch; the dashboard imports it into native Triage. Hermes prepares specifications and dependencies using native orchestration. Ready is dispatch eligibility and may launch work; To-do can promote automatically. Workers request Review. Lee inspects and accepts through Complete, then explicitly returns evidence to GitHub. GitHub closure requires acceptance of the whole issue.

Import is planning permission. An enforced approval stop between planning and automatic dispatch is **not implemented**. This difference from the earlier target remains an open Issue #9 criterion, not permission inferred from a model or card state.

See [workflow](GITHUB_HERMES_WORKFLOW.md), [execution contract](JEEVES_EXECUTION_CONTRACT.md), [execution policy](KANBAN_EXECUTION_POLICY.md) and [checkpoint](HERMES_WORKFLOW_CHECKPOINT.md). Older descriptions of foreground-only ordinary work and pending batch intake are superseded.

Jeeves may optimize execution within the selected scope, not strategy or business priority. Infrastructure work must remain separately authorized and additive. Do not interrupt existing Community Capital/DGX services or expand scope into NCS, model changes or bot deployment as part of ordinary handoff.
