# Canonical guard and evidence limits

Canonical repository file: `execution_guard_v1_final.py`. Mutex: `LandmarkSignalV1Mutex`. The accepted guard holds native Windows ownership for the whole callback/agent lifetime, handles genuine abandonment, denies recursion/non-owner release, and validates child identity, issue binding and boolean approval.

Missing native Windows/pywin32 support fails closed. No file or multiprocessing fallback is authorized. Lock metadata is diagnostic; expiry cannot evict a live native owner. Separate acquire/release CLIs are not the approved execution interface.

PR #20 was merged following Lee's authorization. The native library suite reported thirteen passed tests with one unsupported-platform skip. Issue #19 foreground acceptance verified actual local-model parent/child calls with separate approvals, denied unapproved/wrong-issue callbacks and blocked real contenders. This did not deploy worker bots or accept ordinary detached dispatch.

Issue #7 and Issue #6 document results were accepted; source/evidence are in repository `docs/evidence/issue7/` and `docs/evidence/issue6/`. Read those artifacts for exact run, model, original/corrected hashes and acceptance. Keep historical evidence unchanged. Read `docs/GITHUB_HERMES_WORKFLOW.md` for current accepted routes and remaining limits.

Do not run old path demonstrations, fabricated stale-file checks, obsolete test scripts or historical readiness claims as acceptance. Revalidate affected boundaries when executable behavior changes; do not repeat completed model runs just to update documentation.
