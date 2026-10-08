# Hermes workflow checkpoint — October 7, 2026

## Published and installed

PRs [#28](https://github.com/nvrenuf/landmarksignal-operations/pull/28) and [#29](https://github.com/nvrenuf/landmarksignal-operations/pull/29) were merged into main at `bc21e73f6563b090d4568b424d163d5b557d7212`. Lee's Windows installation and fresh default/Jeeves hook checks succeeded. The normal-account results module loaded and the standalone dashboard reloaded. No model server, SSH tunnel, Desktop or gateway restart was part of that setup.

Validation: 15 intake/dashboard tests, 10 workflow tests and one isolated managed-runpy regression passed (26 total), plus payload checksums, Python compilation and JavaScript syntax. These are the relevant local checks, not a claimed GitHub CI run.

## Real worker and human acceptance

Issue #30 card `t_d1bf319e`, run 29, profile `default`, wrote `WORKFLOW_QUICKSTART.md` in `C:\Users\lee\AppData\Local\hermes\landmarksignal-v1\work\github-intake\f011c99cd7411be169dbe72c`. Lee reported it in Review and supplied the document through a read of that exact workspace. Incorrect workflow claims were corrected twice. The card remained in Review during inspection; Lee then completed it through the dashboard and explicitly returned evidence.

[GitHub return evidence](https://github.com/nvrenuf/landmarksignal-operations/issues/30#issuecomment-6052431163) records the actual task/run/profile/workspace and final local artifact SHA256 `6b4f12fdec7fc0067f654adf06df9549b3e6d1582ee6bf62260ac8367e541b6e`. Issue #30 was closed after Lee authorized acceptance/closure. The returned payload itself conservatively reports acceptance unverified; human acceptance is recorded separately in the issue body.

[WORKFLOW_QUICKSTART.md](WORKFLOW_QUICKSTART.md) transcribes the document contents Lee supplied and the two verified final replacements. It is repository documentation, not an assertion that its bytes match the archived local file hash. The live default-worker path was exercised; a fresh Jeeves-profile native worker was not exercised by this particular checkpoint.

Issue #9 also returned evidence: [actual run 27 result](https://github.com/nvrenuf/landmarksignal-operations/issues/9#issuecomment-6052017405). Its earlier native Done state does not establish acceptance of all its implementation requirements.

## Board cleanup

Lee's cleanup report records 16 cards archived with zero visible cards remaining, no launched/terminated worker, preserved card/run/comment/link/event history, unchanged workspace files and unchanged GitHub records. Full backup: `%LOCALAPPDATA%\hermes\landmarksignal-v1\recovery\board-cleanup-ce91da3e53c644b3a1bb9a1dee993702\kanban.before-cleanup.db`. Two previously archived cards were retained. Archiving unfinished tests is retirement from this visible board, not a passing test or GitHub closure.

## Remaining Issue #9 acceptance

[Issue #9](https://github.com/nvrenuf/landmarksignal-operations/issues/9) remains open in Human Review:

1. Planning-only/unauthorized items lack an enforced approval stop before native dispatch. Ready can launch work and To-do can auto-promote. Resolve through an explicit operating-model decision or scoped enforcement work; do not invent a hidden gate or infer human approval from intake.
2. Human-review result return is demonstrated live. Failure/Blocked mapping and evidence retention passed local tests, but a real failed/blocked task return has not been demonstrated.

Broader Issue #17/#22 requirements, runtime recovery, scheduled/unattended work, universal child authorization, global detached-worker exclusion and model/bot deployment are not proven by this bounded checkpoint. Documentation does not implement those capabilities.
