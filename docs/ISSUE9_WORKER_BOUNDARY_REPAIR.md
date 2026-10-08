# Issue 9 native worker boundary repair

The October 7 Windows report shows that the Jeeves foreground-only policy denied
`kanban_show` and terminal lifecycle reporting. The native workers exited with
code zero without a successful terminal Kanban call; Hermes correctly classified
those exits as protocol violations. There is no evidence that card reads were
intentionally protected against scraping or required manual security review.

This correction permits the native read-only `kanban_list`, `kanban_show` and
`kanban_attachments` tools. A native Jeeves worker can report its own blocker
with `kanban_block(kind="needs_input")` only when the existing read-only board
lookup matches its profile, task, run, claim token and process ID. An environment
label alone does not grant this exception. The native tool handler still checks
ownership. This reports inability to execute; it supplies no execution approval.

Unowned file writes, shell, delegation, task creation, unblocking, completion and
review transitions remain denied. The Issue 19 no-tools acceptance scope remains
denied. Existing owned foreground file scope retains its original checks.

The installer replaces only the inspected Jeeves policy and existing copies in
the launch helper. It normalizes CRLF for old-version comparison, backs up exact
original bytes, refuses unknown versions or running LandmarkSignal cards, and
does not edit configuration or the board. It rolls back replacement failures.
The setup script reloads only the verified standalone browser dashboard on 9119.
Other existing Hermes processes retain their loaded policy until restarted.

Portable checks: 15 tests, 13 passed and two Windows mutex tests skipped. The
Windows setup runs the two new read/claim boundary checks before installation.
No native Windows worker acceptance result is claimed from the portable suite.

## Remaining execution boundary

This fixes observation and safe blocker reporting. It does not connect a native
dispatcher-spawned worker to the foreground guard or create an execution approval
ledger. The default dispatcher/profile remains a separate route. Do not retry
the two blocked subtasks or move them to Ready based on this repair alone.

Before release, verify exact task/run/profile/workspace approval and guard
ownership through the real native worker lifetime; deny launch without approval
across dispatch ticks and reloads; return authorized results to human Review.
Preserve the three completed prototype subtasks and all run/event history.
Do not mark Issue 9 Done, close GitHub issues or change Priority/Execution Order.
