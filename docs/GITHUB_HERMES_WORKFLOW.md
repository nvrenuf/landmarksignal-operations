# GitHub to Hermes workflow

## Authority and current implementation

Lee selects priorities, approves scope and authorizes execution. ChatGPT advises and reviews. GitHub Project #3 is the authoritative backlog, dependencies, priority, Execution Order, Sprint, issue/PR and published-evidence record. The existing LandmarkSignal Hermes board records local task/run state. A completed Hermes subtask does not close a broader GitHub issue.

This document defines the agreed workflow and distinguishes it from implemented capability. Explicit approval never follows merely from a GitHub status, a card move, an assignee or a title.

## Selected-issue workflow

| Stage | Intended behavior | Current implementation / boundary |
|---|---|---|
| GitHub backlog | Select one issue and bounded deliverable; do not mirror the whole project. | GitHub CLI access as nvrenuf was verified in Lee's PowerShell, not inside Jeeves. |
| Triage | Preserve source URL, original requirements, updated timestamp and source hash; prepare a specification. | Native card creation and specification exist. Reusable issue intake and guarded specification are not yet connected. Import permission is not execution permission. |
| To-do / specification review | Review scope, deliverable, acceptance criteria, dependencies and questions. | Native To-do can automatically become Ready. Do not use it as an approval hold. Until a verified review hold exists, approved routes use native sticky Blocked holds. |
| Ready / Scheduled | Explicitly release the exact reviewed task and scope for immediate or timed execution. | Existing guarded document launcher supports two reviewed contracts. Scheduled waits on time; it does not supply approval. General scheduled execution is unverified. |
| In Progress | Execute under the guard for the whole work lifetime. | Two no-tools document tasks and the foreground acceptance route were validated. Ordinary dispatcher and tool-enabled workers are not accepted. |
| Review | Return output and evidence; Lee accepts or requests changes. | Document pilots returned to native Review and were accepted. |
| Done | Complete only the accepted card; publish results to GitHub and assess all issue criteria. | Issue #7 and #6 document cards completed. Broader GitHub issues remain open. Publication currently occurs manually through reviewed PRs. |

Lee may authorize intake and bounded specification drafting together. Do not ask again for steps already covered by that explicit scope. Implementation and child work still require their applicable distinct authorization.

## Existing native capabilities and the missing connection

Reviewed Hermes revision: `0c2ff854a5c5121c75ac0b0a35241a580ee27fb7`.

- `hermes_cli/kanban_parser.py` exposes task creation with `--triage` and single-task `specify`.
- `hermes_cli/kanban_specify.py` uses the configured auxiliary `triage_specifier` model, not necessarily Jeeves's primary model.
- `hermes_cli/kanban_db.py::specify_triage_task` calls `recompute_ready` after updating the spec. A parent-free card can become Ready immediately.
- The native dashboard specify route invokes this auxiliary path; the agent pre-tool hook does not establish guard coverage for this direct route.
- Manual orchestration disables automatic decomposition, not every specification, promotion or worker path.
- `kanban boards import` imports an exported Hermes archive into a new board. It is not GitHub issue/project synchronization.
- The installed Jeeves policy permits planning reads but denies unowned shell commands and task mutations. Successful `gh` access in PowerShell does not establish policy-permitted agent access.

Sources: [native parser](https://github.com/NousResearch/hermes-agent/blob/0c2ff854a5c5121c75ac0b0a35241a580ee27fb7/hermes_cli/kanban_parser.py), [specifier](https://github.com/NousResearch/hermes-agent/blob/0c2ff854a5c5121c75ac0b0a35241a580ee27fb7/hermes_cli/kanban_specify.py), [database transitions](https://github.com/NousResearch/hermes-agent/blob/0c2ff854a5c5121c75ac0b0a35241a580ee27fb7/hermes_cli/kanban_db.py), [dashboard API](https://github.com/NousResearch/hermes-agent/blob/0c2ff854a5c5121c75ac0b0a35241a580ee27fb7/plugins/kanban/dashboard/plugin_api.py).

Next implementation boundary: reuse authenticated GitHub reads and native Kanban creation; add a narrow trusted intake/approval path only where needed. Before enabling it, bind the exact issue/task/workspace/source snapshot, prevent duplicate intake, preserve the original source separately from model-written specs, keep an explicit hold against promotion, verify the auxiliary route/model, and prove no child creation or ordinary worker launch occurs. Do not relax the global tool hook or enable automatic decomposition to achieve intake.

## Current operating procedure

Use the existing Jeeves Launch tab at `http://127.0.0.1:9119/jeeves-launch?profile=jeeves` only for installed, reviewed document contracts. Completed documents remain readable and are not relaunched. New contracts require source review. Do not click the ordinary dispatcher, native Specify or Decompose for new work until their intended guarded route is reviewed and verified.

One participating guarded LandmarkSignal execution at a time. Child creation and execution each require the applicable explicit scoped human authorization; parent approval does not imply either. No bot deployment, priority/order/sprint changes, issue closure, production merge, infrastructure change or external cost follows from importing a task.

## Documentation precedence

Use current explicit Lee decisions, then the operating model and execution contract for authority, this workflow and execution policy for procedures, and dated artifacts for evidence. Documents do not grant capabilities missing from executable code. If instructions conflict, report the exact conflict; do not choose a permissive interpretation. Historical reports and pre-reconciliation skill references are evidence only, not launch instructions.
