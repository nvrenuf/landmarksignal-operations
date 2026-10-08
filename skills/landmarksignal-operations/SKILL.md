---
name: landmarksignal-operations
description: "Operate LandmarkSignal's GitHub-to-Hermes intake, native Kanban work, human review and explicit evidence return. Use for Jeeves coordination, selected GitHub issues and the LandmarkSignal board."
---

# LandmarkSignal Operations

Use repository `nvrenuf/landmarksignal-operations`, GitHub Project #3 (`https://github.com/nvrenuf/projects/3`) and the existing `landmarksignal` Hermes board. Lee controls scope, Priority, Execution Order, Sprint, acceptance, merges and deployments. Do not create replacement boards or fields.

Follow the current repository `docs/GITHUB_HERMES_WORKFLOW.md`, `docs/JEEVES_EXECUTION_CONTRACT.md`, `docs/KANBAN_EXECUTION_POLICY.md` and `docs/HERMES_FOLDER_MAP.md`. Read the matching local reference below. Treat other retained skill references as historical; report conflicts rather than following obsolete commands.

| Operation | Read |
|---|---|
| Import queued issues and native Kanban lifecycle | `references/hermes-kanban.md` |
| Tools, scope, dispatch and review boundaries | `references/hermes-kanban-safety.md` |
| Read-only board inspection (retained supplemental reference) | `references/kanban-inspection.md` |
| Workspace inventory (retained supplemental reference) | `references/workspace-inventory.md` |
| Foreground guard and its evidence limits | `references/execution-guard-v1.md` |
| Acceptance evidence and remaining gaps | `references/acceptance-test.md` |

Verify the authenticated GitHub account is nvrenuf and freshly read the exact repository/issue before permitted GitHub operations. Use the installed GitHub skill for syntax. Do not print credentials or change authentication automatically.

Lee selects Project Status **Queued for Jeeves**, then clicks **Import queued work**. The existing importer pulls the eligible batch into unassigned Triage, preserving original requirements, source identity and dependencies. Repeated imports reuse existing identities, including archived cards. Do not reset archived cards or create duplicates to replay work.

Use ordinary native Hermes project tools within the task's authorized scope. Hermes may specify/decompose work and resolve dependencies. To-do may auto-promote to Ready; Ready is the native dispatch queue and can launch automatically. Do not claim a separate approval stop exists there. Import is planning selection, not unlimited execution authorization. If a task lacks required authorization, report its blocker through the permitted native lifecycle; do not bypass it or invent approval.

Workers call `kanban_request_review` and stop at Review. Workers must never call `kanban_complete`, including after verbal acceptance. Lee uses dashboard **Complete** after inspecting the actual deliverables. Lee explicitly clicks **Send results to GitHub Human Review/Blocked** to return actual run evidence. Do not claim automatic synchronization, file uploads, issue closure or acceptance from a worker summary.

Preserve Priority, Execution Order, Sprint and original requirements. Obtain explicit approval for scope expansion, merges, deployments, external costs or production/security changes. Parent work does not automatically authorize unrestricted child work. Ordinary native dispatch is not covered by the separate Issue #19 foreground mutex proof.

Preserve existing DGX production services. Do not restart/rebind/replace services, change models, deploy the planned roster or broaden infrastructure access as part of a handoff.

Distinguish installed capabilities, tests, live evidence and unresolved requirements. Issue #9 remains open: dispatch approval enforcement is not implemented, and live Blocked-result return is not yet demonstrated. Never turn historical readiness claims into acceptance.

## Read-only inspection and document review

During inspection, read cards and exact workspace files without changing cards, launching workers or completing tasks. Distinguish connected workflow, local-only code and untested claims. If permitted by scope, inspect git status/diff/log before reporting changes. A clean working tree does not prove that nothing was committed, pushed or changed on GitHub; verify those claims separately.

For the operator quickstart, read `WORKFLOW_QUICKSTART.md` from the card's exact workspace. Keep documentation consistent with the current seven-step workflow: Project #3 planning, explicit queued batch import, native preparation and Ready eligibility, worker Review, Lee's dashboard Complete, explicit evidence return without issue closure, and Lee's Priority/Execution Order/Sprint and merge/deploy authority. Do not substitute a stale chat working directory or claim automatic synchronization or attachments. Preserve task-specific length and deliverable requirements.

Retain the supplemental inspection/inventory references and other unrelated resources. Their contents were not part of this five-file reconciliation. If a supplemental reference conflicts with this skill or current repository policy, follow the current policy and report the conflict.
