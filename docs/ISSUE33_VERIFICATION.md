# Issue #33 verification — October 8, 2026

Implementation is prepared for Lee's review. Issue #33 remains open and unqueued; no merge or acceptance is implied.

## Verified installation

- GitHub authenticated as `nvrenuf`; main fetched at `8d011a45d5d39203b1984ae42b17d2531a127dd5`.
- Installed Hermes revision remains `0c2ff854a5c5121c75ac0b0a35241a580ee27fb7`.
- Verified Project #3 identity `PVT_kwHOAFD_484BlSRq` and Project #4 identity `PVT_kwHOAFD_484BmKAG`.
- Project #4's existing Status field `PVTSSF_lAHOAFD_484BmKAGzhk0Hdw` now includes Queued for Jeeves, Human Review and Blocked. The original Todo, In Progress and Done IDs/options and all captured item values were unchanged. No Project #3 field was modified.
- Five installed launcher payload hashes matched the focused manifest. Normal Lee could import all three companion modules after managed bootstrap. Protected file maintenance preserved original file/directory protections and granted the new helper normal-user read/execute.
- Both installed project connections passed read-only checks: zero queued issues and zero returnable results. No import or result-send action was invoked against real work.
- The independently identified standalone port 9119 dashboard was reloaded as normal Lee. Before reload, the board had 18 archived cards, zero active worker/claim markers and zero unfinished runs. No Desktop, gateway, model server or infrastructure restart was performed.
- Browser verification showed both selector options, Project #3 as the initial source, and Project #4 as the active source after selection. Refresh results worked for the selected project. The historical approved-document panel still reports “Expected exactly one prepared document card” for its archived pilot; that pre-existing panel is outside this change.

## Tests passed

- `run_github_projects_checks.py`: 53 targeted tests, including selection isolation, source identity/hash validation, dependencies, duplicate batches, archived cards, Project #3 compatibility, exact result routing, mismatches rejected before writes, unchanged native records, worker Review policy, installer backups/rollback and managed isolated-runpy imports.
- `verify_github_projects.py --fixtures`: 12 isolated mutation fixtures using the **installed** intake/results modules, plus normal-user checksum/import and live read-only connection checks.
- `node --check plugins/landmarksignal-launch/dashboard/dist/index.js` and `git diff --check` passed.

## Local recovery records

All locations below are under `C:\Users\lee\AppData\Local\hermes\landmarksignal-v1\recovery`:

- Original launcher files and rollback mapping: `github-projects-23be5b6a1c234793afd62fe109e79557\paths.json` and its `.before` files.
- Original file/directory ACLs and successful maintenance report: `github-projects-acls-b0d30e69ff7b4005b15efc43ea9299b8`.
- Project #4 field/item snapshots before and after: `project4-status-0f6fe53aae0442bfaa69171bffa59491`.
- Standalone dashboard reload logs: `github-projects-dashboard-2cbe583351bb47a5ad87f39a000c0ecc`.

The original checkout and its unrelated modifications were preserved. This work used an isolated worktree and branch.

## Acceptance limits

Lee still needs to review the implementation and bounded live connection check. An actual live import/return round trip was deliberately not performed: neither project has queued work, and synthetic production cards/evidence were prohibited. A separately approved real item is required for such a mutation check. No worker launch, execution approval, issue closure or PR merge was performed. The separate pre-dispatch approval gap remains outside Issue #33.
