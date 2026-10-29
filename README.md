# LandmarkSignal Operations

Planning, issue tracking and the supervised GitHub-to-Hermes workflow for LandmarkSignal.

## Current checkpoint — October 7, 2026

PRs #28 and #29 are merged. The manual GitHub queue import, native worker Review and explicit GitHub evidence return are installed on Lee's Windows laptop. Issue #30 exercised a real default-profile worker: it stayed in Review during corrections, Lee accepted it through Complete, and its artifact evidence returned to GitHub. Issue #30 is closed; Issue #9 remains open in Human Review with two outstanding criteria.

The visible LandmarkSignal Kanban was cleared by archiving 16 existing cards. All card/run/comment/dependency history and workspace files were preserved with a database backup. Archived cards remain linked to their GitHub issues; importing an archived issue again does not reset or duplicate it.

## Start here

- [Operator quickstart](docs/WORKFLOW_QUICKSTART.md): the accepted Issue #30 document.
- [GitHub-to-Hermes workflow](docs/GITHUB_HERMES_WORKFLOW.md): implemented behavior and remaining limits.
- [Hermes runtime topology](docs/HERMES_RUNTIME_TOPOLOGY.md): canonical root/profile/gateway/Kanban/skills/Hindsight relationships and new-session resume rules.
- [Hermes folder map](docs/HERMES_FOLDER_MAP.md): detailed runtime, profiles, plugins, board, artifacts and backups.
- [Operating model](docs/OPERATING_MODEL.md) and [Jeeves execution contract](docs/JEEVES_EXECUTION_CONTRACT.md): authority and scope.
- [Execution policy](docs/KANBAN_EXECUTION_POLICY.md): actual controls and their limits.
- [Acceptance checkpoint](docs/HERMES_WORKFLOW_CHECKPOINT.md): evidence and outstanding work.

GitHub Project [#3](https://github.com/nvrenuf/projects/3) holds priorities, Execution Order, Sprint, approvals and published evidence. The existing `landmarksignal` Hermes board records local execution. Ready can launch native work; worker output goes to Review; Lee accepts through Complete. Return evidence through the dashboard button. GitHub closure is a separate human decision.

The Jeeves launcher also supports the explicitly selected [Hermes Optimization Project #4](https://github.com/users/nvrenuf/projects/4). Select the source before import or result return; both projects use the existing launcher and board. See the [workflow and focused installation instructions](docs/GITHUB_HERMES_WORKFLOW.md) and [Issue #33 verification](docs/ISSUE33_VERIFICATION.md).

This repository contains maintained integration source and documentation. It is not the installed upstream Hermes runtime, a backup of the entire Hermes folder, or proof that uncommitted laptop files were pushed. Do not commit credentials, live databases or model files.

Historical pilots and repair reports remain as evidence. Use the current documents above for operation; do not reinstall old repair scripts merely because they remain in the repository.
