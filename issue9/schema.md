# GitHub / native Hermes binding

GitHub Project 3 selects queued work. The existing intake control creates exactly one Triage root per stable project/issue identity. An edited issue body is a new source revision, not a new task identity.

| Value | Source |
|---|---|
| Issue URL/repository/project/item | Actual GitHub issue and Project item |
| Priority, Execution Order, Sprint | Existing GitHub fields; never inferred |
| Board/task/workspace | Existing native Kanban card |
| Run/profile/outcome/summary | Actual native task_runs record |
| Artifact evidence | Existing files and their SHA256 hashes |
| Human acceptance | Separate human review decision; never inferred from Done |

Queued for Jeeves imports to Triage. Native Ready is execution eligibility. Native running returns In Progress; review or historical Done returns Human Review; blocked/crashed returns Blocked. Returning evidence does not close issues or authorize more work.

The approval utility requires an explicit issue/task-bound approval record if used. It does not intercept the native dispatcher. Native task lifecycle controls and human release govern work. Worker output must request review; Lee completes it using the dashboard. Actual installed hook and round-trip verification remain required before accepting this correction.
