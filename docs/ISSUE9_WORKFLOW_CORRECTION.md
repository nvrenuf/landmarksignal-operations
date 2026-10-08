# Issue 9: focused workflow correction

The reviewed worker output had reproducible defects: broken status mapping, automatic priority-to-sprint reassignment, permissive empty approvals, placeholder task IDs, and failure evidence omitted from return payloads. Native Done reflected worker reports, not acceptance.

## Installed changes

- Preserve the existing manual GitHub Project 3 batch button and stable issue-key deduplication. Import stays Triage; new snapshots also retain Priority, Execution Order and Sprint values without remote writes.
- Replace the four reviewed workspace prototypes with corrected modules; preserve exact original bytes in the installation backup. Do not rewrite source snapshots, events, cards or historical completion states.
- Enable the same narrow review hook in default and Jeeves. Native project tools remain available. `kanban_complete` on the LandmarkSignal board returns an instruction to call `kanban_request_review`; human dashboard Complete remains available. This is a workflow control, not OS isolation against an agent deliberately invoking raw CLI/database methods.
- Disable automatic review dispatch in default/Jeeves and keep configured concurrency at one. Other profiles and production services are untouched. Existing unrelated runtimes need reloading before they see new config/code.
- Mount explicit results inspection and return routes in the existing dashboard. Return binds the actual root task/latest run/profile/workspace, artifact hashes and Project item. It deduplicates issue comments and sets only Human Review or Blocked, then freshly verifies remote Status. Native Done never maps directly to GitHub Done. The issue must still be open.

## Approval and remaining verification

Ready remains native dispatch eligibility; native To-do can auto-promote when prerequisites complete. This patch does not claim a new pre-dispatch approval supervisor. Lee controls release using the existing native workflow. The record-level approval helper is a validation utility, not a dispatcher interceptor.

The return button reports worker claims and local file inventory as awaiting acceptance. It does not invent passing tests, run IDs or human approval. A local artifact hash is not a remote PR. The original output remains rejected until code review and a real installed round trip succeed.

Run setup_issue9_workflow.ps1 from a pinned checkout. It runs the ten correction tests, elevates only installation, verifies actual installed pre-tool hooks in fresh default/Jeeves Python processes, and reloads only the normal-user standalone browser dashboard on 9119. Desktop/gateway/model/tunnels are not restarted. No task or GitHub write is performed by setup.

Local validation: ten correction tests and fifteen existing intake/dashboard tests pass; JavaScript syntax and Python compilation pass. Windows ACL/config installation, live GitHub schema/authentication, actual installed hooks and a subsequent real worker round trip are verified on Lee's laptop, not claimed from the Linux test environment. PR remains unmerged.

## New-module permission correction

The first Windows install created github_handoff_results.py with administrator ownership and inherited OWNER RIGHTS, leaving the normal dashboard account unable to read it. The maintenance step now adds only a ReadAndExecute allow ACE for the expected Lee SID on manifest entries that were newly introduced. Existing owner and other access rules remain. Setup directly imports and inspects the installed results module as the normal user before dashboard reload. The review buttons also have explicit visible styling.
