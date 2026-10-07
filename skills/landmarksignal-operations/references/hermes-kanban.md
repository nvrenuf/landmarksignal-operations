# Selected issue and Kanban workflow

Read the current repository `docs/GITHUB_HERMES_WORKFLOW.md`, `OPERATING_MODEL.md` and `JEEVES_EXECUTION_CONTRACT.md`. Use the existing LandmarkSignal board; do not initialize/reset/export/import another board for this workflow.

Target: selected GitHub issue -> Triage specification -> To-do dependency resolution -> Ready waiting for Lee's execution approval -> guarded In Progress -> Review -> accepted Done. GitHub retains the full backlog; Hermes receives selected bounded work only. Preserve full issue URL and original requirements separately from derived specs, record source version/hash and prevent duplicates.

Native card creation, single-task Specify and eight columns exist in revision `0c2ff854a5c5121c75ac0b0a35241a580ee27fb7`. Specify uses `auxiliary.triage_specifier`, which may not be the primary Jeeves model. Specify calls recompute_ready: parent-free To-do tasks can immediately become Ready. Allow normal promotion to Ready; gate execution at launch rather than blocking this promotion. Ready must remain idle without Lee's exact-scope approval. Scheduled is a time wait, not approval. Manual orchestration disables auto-decomposition only.

Reusable intake and guarded specification are not yet connected. Do not run native Specify/Decompose or ordinary dispatcher to fill that gap. Use a reviewed narrow entry that enforces the approval and lifecycle, or report the missing entry. The completed document pilots used native sticky Blocked holds before release; retain those records, but do not require a Blocked hold for the future reusable Ready workflow. Verify the actual dispatch paths and that unapproved Ready cards stay idle before enabling that workflow. Completion and card creation never grant implementation permission.

Use the Jeeves Launch tab at `http://127.0.0.1:9119/jeeves-launch?profile=jeeves` for the two installed reviewed document contracts. Completed documents stay readable; do not replay them. New contracts require source review. Returning work to Review is part of the approved run; Lee accepts before completing a card. Assess every GitHub issue criterion before closing the issue.

Named board database: `%LOCALAPPDATA%\hermes\kanban\boards\landmarksignal\kanban.db`. Do not assume a root/profile database is the same board. Verify runtime/profile and installed revision before using native APIs. Do not assume Desktop/browser share state unless they resolve the same Hermes root and named board.
