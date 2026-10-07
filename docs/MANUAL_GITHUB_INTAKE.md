# Manual GitHub queue intake

This is the Issue #9 intake slice: one dashboard button imports a selected batch into the existing LandmarkSignal board's native Triage column. It does not add a polling service, GitHub Action, board, agent, specification runner or ordinary execution launcher.

## Operator workflow

1. Select work in nvrenuf GitHub Project #3 using the existing **Queued for Jeeves** Status.
2. Open **Jeeves Launch** at http://127.0.0.1:9119/jeeves-launch?profile=jeeves.
3. Click **Import queued work** once. The authenticated route reads all project pages and imports newly queued open issues into Triage. Archived items, draft items, PRs and closed issues are excluded.
4. Read the batch result, then open the existing LandmarkSignal Kanban. New cards remain unassigned and unclaimed. Original source URL, body, updated timestamp, SHA256, project/item/issue identities and structured GitHub blocking dependencies are retained in the card and separate source JSON.
5. Continue preparation using the existing reviewed Kanban procedures. This intake change neither validates nor enables a general specification/Ready-worker execution path. The previous two accepted document routes remain available. Ready and assignment are not execution authorization.

GitHub priorities, Execution Order, Sprint, statuses and authorization values are never written. A queued item is not moved out of the GitHub queue on import; repeats report the existing card instead. All statuses, including archived imported cards, are preserved. A queued issue with an existing canonical source-linked card is reported as already linked; it is not reset or relaunched. Multiple linked cards or changed orphaned source snapshots require manual review.

GitHub dependency records are preserved as source facts, not converted automatically into Kanban parents or new prerequisite cards. Specification, resolving unclear dependencies, mapping dependency edges, promoting to Ready and approved execution are subsequent workflow steps, not claimed by this intake slice. Native model routing and approval controls are unchanged.

## Installation and evidence

The installer verifies the reviewed Hermes revision, unchanged native Kanban files, existing launcher/guard, conservative Jeeves dispatch flags, nvrenuf authentication and Project #3 queue reads. It rejects unknown launcher edits, backs up the entire existing plugin, normalizes payload CRLF before hashing, updates only the API/UI and the new intake module, verifies installed hashes and rolls back failed file replacement. No card is created during installation.

The setup script checks the existing port-9119 dashboard's executable, command, Windows owner, creation time and absence of a Hermes Desktop ancestor before restarting only that browser dashboard. Native Windows installation/live import evidence is pending until Lee returns the saved Desktop report and exercises the button.

Each import serializes through the existing Windows execution mutex, reads dependencies before writing, backs up the board, uses native `create_task(triage=True)` in one explicit transaction, and verifies every pre-existing task row is unchanged before commit. It does not initialize or migrate a board, invoke a model, claim a task, spawn a worker, approve a child or change infrastructure.

Portable checks cover account refusal, pagination/filtering/dependency preservation, batch idempotency, canonical source-link identity, whole-batch rollback, running-task refusal, cross-origin refusal, no worker spawning, CRLF payload handling, unknown-edit refusal and installation rollback. Existing document launch checks also pass. These checks do not substitute for native installation and a real GitHub-to-Triage import.
