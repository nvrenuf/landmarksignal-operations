# Native tools, scope and human review

Read repository `docs/KANBAN_EXECUTION_POLICY.md` and `docs/JEEVES_EXECUTION_CONTRACT.md`.

Ordinary native project tools are available under existing Hermes approval settings. The obsolete foreground-only restriction has been removed. Read cards and permitted workspace files normally; do not invent scraping prohibitions or claim reads need guarded execution.

The installed default/Jeeves hook prevents worker `kanban_complete` on the LandmarkSignal board. Request Review instead. Lee completes through the dashboard. Review dispatch is configured false; concurrency limits are configured to one. These settings are not proof of a global mutex across every process/profile.

Ready is dispatch eligibility. To-do can auto-promote and Ready can launch work. A separate explicit pre-dispatch approval interceptor has not been implemented. Do not claim that choosing a planning Status creates an execution approval record. Where the requested scope requires approval, obtain it or report a native blocker; do not forge records or broaden scope.

Keep original requirements, source identity and actual task/run/profile/workspace evidence. Preserve human Priority, Execution Order and Sprint. Parent scope does not automatically approve child scope or production changes. Existing Hermes approval settings remain applicable.

Use native blocker reporting for actual blockers and Review for deliverables. Report tests actually run, not demonstrations as live integration. Never call Complete as a way to unblock, retry or request approval.

The Issue #19 foreground guard is a separate participating route; its ownership/child checks do not establish universal native dispatcher enforcement. Do not restore its obsolete blanket tool gate.

## Native worker terminal protocol

When genuinely waiting on Lee's input or another blocker, call the permitted `kanban_block` with a clear reason before ending the worker run. For deliverables awaiting acceptance, call `kanban_request_review`. Merely asking a question and exiting cleanly does not record the native lifecycle outcome and can cause protocol failures/retries. Do not use `kanban_complete` to satisfy the worker protocol or recreate the obsolete foreground gate.
