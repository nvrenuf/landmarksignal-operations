# Manual Jeeves document handoff

GitHub is the issue and priority record. The existing LandmarkSignal Hermes board records execution. Creating or preparing a card does not authorize a model call.

The dashboard selector lists source-reviewed document contracts. It accepts no arbitrary prompts, commands, workspace paths, model routes or repository URLs from the browser. The first additional contract is a one-page planned roster draft under Issue #6. It does not create bots or child tasks and does not complete the whole issue.

## Prepare and run

1. Use the pinned setup checkout and run `setup_document_handoff.ps1` from Lee's ordinary PowerShell. It verifies the existing native Jeeves browser dashboard owner before changing files. Desktop-managed dashboards are refused rather than killed.
2. Preparation backs up the existing board and launcher assets, checks reviewed installed hashes, and creates or finds the exact Issue #6 card using a stable idempotency key. The new card and native sticky blocked event are committed together. All existing cards, including the completed Issue #7 card, are preserved. Model, policy and configuration values are not changed.
3. The script restarts only the browser dashboard to mount the expanded routes. No model call or dispatch occurs during setup.
4. In `http://127.0.0.1:9119/kanban?profile=jeeves`, select Issue #6's planned roster draft and expand **Review exact task scope**. Type **APPROVE ISSUE 6**, then select **Approve and run**. Do not use the ordinary dispatcher.
5. The launcher binds the card snapshot, reviewed contract, task ID, issue URL, profile and fixed workspace. It rejects wrong approvals, unreviewed selectors, competing running work and duplicate launches. The worker rechecks the card under the accepted global mutex before an exact native claim.
6. Jeeves gets one bounded local-model document call: 1800 output tokens, one iteration, 120-second run budget, no tools or children, no fallback model. Saved reasoning/model settings are unchanged. Ownership lasts through agent close. Missing required role names or incomplete model output stops the run without publishing a successful draft.
7. The document and evidence go to native Review. Inspect content; Lee decides acceptance. Complete only that card after acceptance. Return accepted artifacts and evidence to GitHub manually, and close a GitHub issue only when all its criteria are met.

## Scope and evidence limits

The existing Issue #7 pilot was accepted and merged in PR #23. Its card, document, original run evidence and review corrections are retained.

This change adds a reviewed document-contract catalog and an Issue #6 drafting task. New contracts must be defined and reviewed in source before appearing in the dashboard. It is not arbitrary-task import, automatic GitHub synchronization, a bot deployment mechanism, tool-enabled execution or proof of ordinary dispatcher supervision.

Portable tests cover launch boundaries, idempotent card preparation, manual-hold publication and asset upgrade checks using temporary databases and stubbed host/worker APIs. The native dashboard displayed the expanded selector and Issue #6 reached Review. Uploaded run #14 evidence verifies the reviewed contract and task-body hashes, one actual local-model call with no tools exposed, ownership through agent close, and original-card preservation. Lee accepted the document after three wording corrections and reported the card completed to Done. The completion is human-reported, not an independent database inspection. Original run evidence remains in its historical Review state; the correction and subsequent acceptance are separate records. See `docs/evidence/issue6/`. A failed launch is recorded for review; there is no automatic retry or marker deletion.
