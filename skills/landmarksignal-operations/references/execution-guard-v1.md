# Foreground guard and evidence limits

Canonical repository implementation: `execution_guard_v1_final.py`; Windows mutex: `LandmarkSignalV1Mutex`. The participating foreground guard holds ownership through execution, handles genuine abandoned mutexes and verifies issue-bound child approvals. Missing native Windows/pywin32 support fails closed. Metadata expiry cannot evict a live owner. Do not use detached acquire/release commands or fallback locks as equivalent proof.

PR #20 was merged following Lee's authorization. Issue #19 foreground acceptance verified actual local-model parent/child calls with distinct approvals, rejected unauthorized/wrong-issue callbacks and blocked real contenders. Preserve its evidence; do not rerun merely to refresh instructions.

Ordinary native Hermes project tools now use the current native workflow and review hook. The foreground trial is not a global native dispatcher lock or proof of universal child-authorization enforcement. Do not require obsolete foreground-only launch entries for normal card reads or scoped project work.

Read repository `docs/HERMES_WORKFLOW_CHECKPOINT.md` and `docs/GITHUB_HERMES_WORKFLOW.md` for current evidence and limits. Preserve historical artifacts and record later decisions separately.
