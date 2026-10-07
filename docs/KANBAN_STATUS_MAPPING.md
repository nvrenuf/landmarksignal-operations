# KANBAN_STATUS_MAPPING.md

## GitHub Stage to Hermes Interpretation

| GitHub Stage | Hermes Interpretation |
| :--- | :--- |
| **Idea** | Planning phase; no dispatch initiated. |
| **Defined** | Specification complete; no dispatch initiated. |
| **Sprint Ready** | Planned and dependency-checked; no dispatch initiated. |
| **Queued for Jeeves** | Human-approved handoff; blocked until manual release, then ready. |
| **In Progress** | Running under owned guard. |
| **Validation** | Evidence checks occurring during the run; not a native state. |
| **Human Review** | Review phase. |
| **Blocked** | Blocked state. |
| **Done** | Completed after human acceptance. |

## Operational Rules

1.  **No Implicit Permission:** GitHub status never grants execution permission. Execution requires explicit approval and the guarded launcher.
2.  **Binding Scope:** Approval binds the specific issue, task, and workspace. It does not propagate to sibling issues or unrelated tasks.
3.  **Guarded Execution:** Only one guarded task runs per approval. Child tasks require separate, distinct approvals.
4.  **Evidence Preservation:** All artifacts and evidence generated during validation must be saved to the review folder before transition to Human Review.
5.  **Human Acceptance:** The status transitions to `Done` only after Lee explicitly accepts the output. Merging occurs post-acceptance.

## Verification Notes

Parent/child safety checks for Issue 19 passed; this task operates without tools or children. The runner retains the mutex through agent close. Native manual holds use blocked events to prevent automatic promotion until an approved manual release. Manual orchestration explicitly disables automatic decomposition.

**Unverified:** Ordinary native dispatcher guard integration, automatic GitHub synchronization, and startup recovery remain unverified.
