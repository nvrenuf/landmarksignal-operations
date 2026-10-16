# Jeeves execution contract

## Ordinary native project work

Use the exact GitHub issue, named board, task/run identity and assigned workspace. Read the requirements, use tools needed within authorized scope, produce verifiable artifacts, report genuine blockers and submit output through `kanban_request_review`. Default/Jeeves ordinary project tools are available; the obsolete foreground-only tool gate is removed.

Finish at Review. Do not call `kanban_complete` for LandmarkSignal work; Lee accepts through dashboard Complete. Do not claim success based on demo output, generated summaries or the mere existence of code. Return the actual file paths and meaningful verification performed.

## Authority and boundaries

Lee controls scope, Priority, Execution Order, Sprint, acceptance and GitHub closure. Obtain applicable explicit authorization for scope expansion, merges, deployment, external cost, deletion, credential/access changes and production infrastructure changes. Jeeves cannot approve those actions itself. Permission for steps already included in an explicit scope does not require repetitive confirmation.

Decomposition and worker handling may occur through the configured native Kanban workflow. Neither the current hook nor a parent task establishes universal issue-bound child approval enforcement. Do not represent the Issue #19 synchronous acceptance route as enforcement of all ordinary workers or children.

## Actual execution behavior

Ready can dispatch automatically; To-do can auto-promote after prerequisites complete. Queue import is a planning action and does not itself establish execution authorization. The required approval stop before planning-only work dispatches is still unimplemented; report this limitation rather than claiming a hidden manual gate exists.

The installed hooks require worker Review, allow ordinary project tools and preserve explicit tool-free acceptance calls. They are workflow controls, not an OS sandbox against direct CLI/database bypass. Existing native approvals and configured concurrency remain; global detached cross-profile guard coverage is not claimed.

## GitHub Projects V2 issue and status operations

For routine project-board operations, use the authenticated GitHub CLI from the **actual worker execution environment**. Windows and `LandmarkSignal-Ubuntu` WSL may have different `gh` installations, configuration files and OAuth scopes; verify with `gh auth status` and an authenticated project read before assuming access. Never print, request in chat, copy between environments or commit access tokens. If permissions are missing, report the blocker and request human authorization.

Prefer the native CLI for supported operations: `gh project item-list`, `gh project item-add`, `gh project field-list`, and `gh project item-edit`. For a Status update, obtain the **project ID**, **project item ID**, **Status field ID**, and **single-select option ID** from live CLI output and use `gh project item-edit --id <item-id> --project-id <project-id> --field-id <field-id> --single-select-option-id <option-id>`. Do not confuse an issue number with a project item ID. Check whether each issue is already on the board before adding; operations must be idempotent.

Use GraphQL only for Projects V2 operations not supported by the installed `gh` version, and validate results with an independent read. Do not switch to GitHub REST expecting it to support Projects V2 custom-field mutations. Record verified commands, field/option mapping, item links and post-write status evidence in the task's GitHub issue. Avoid speculative API retries or permission changes.

Follow each project's **actual** status options and launcher configuration; never assume all projects have identical fields, or that setting a queue status authorizes execution. Preserve dispatch/concurrency controls and the human-review boundary. This guidance applies to LandmarkSignal, Career Operations and other authorized GitHub Projects.

## Review, return and escalation

Lee reviews actual artifacts and requests scoped corrections or accepts through Complete. Explicit GitHub result return posts execution evidence and sets Human Review or Blocked; it never closes the issue. Native Done, a subtask completion or a merged support PR is not blanket issue acceptance.

If work cannot finish, use `kanban_block` with the specific blocker. Avoid repeated retries that conceal errors. Do not bypass a legitimate control to change unapproved scope. Distinguish an actual technical denial from obsolete text in an old skill or report.

Use [workflow](GITHUB_HERMES_WORKFLOW.md), [execution policy](KANBAN_EXECUTION_POLICY.md) and [folder map](HERMES_FOLDER_MAP.md). Read-only card inspection is allowed. Historical no-tools document contracts remain separate bounded routes, not the only current execution route.
