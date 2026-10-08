# Issue 9 correction

These modules replace the local prototypes reviewed on October 7. They preserve human-selected sprints and stable issue identity, require supplied native task/run bindings, retain failure evidence, and map native completion to Human Review.

Live integration is the existing batch intake plus github_handoff_results.py mounted by the existing dashboard plugin. GitHub return is an explicit authenticated dashboard action; it writes an idempotent issue comment and updates only the existing Project 3 Status field. It never closes an issue or assigns Sprint/Priority/Execution Order.

The approval helper validates supplied execution records. It is not the Hermes dispatcher. Native Ready remains the execution queue; native To-do can become eligible automatically when dependencies finish. This correction enforces review of worker output, not an upstream dispatcher redesign.

Old card Done states and run summaries remain historical records and are not accepted evidence. Corrected code and local tests require installed-hook verification and a real round trip before accepting Issue 9.
