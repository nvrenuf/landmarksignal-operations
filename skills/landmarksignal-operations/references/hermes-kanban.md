# Native GitHub-to-Hermes workflow

Use Project #3 as the planning/priority record and the existing LandmarkSignal board for native execution. Read repository `docs/GITHUB_HERMES_WORKFLOW.md` for the current procedure.

1. Lee selects issues with Project Status **Queued for Jeeves**.
2. Lee clicks **Import queued work** in the existing Jeeves dashboard. The eligible batch becomes unassigned Triage cards; original requirements, exact issue identity and recorded dependencies are preserved.
3. Hermes specifies/decomposes work where appropriate. To-do can auto-promote when dependencies are satisfied. Ready can launch automatically; it is not a separate human approval queue.
4. Workers use the tools allowed by the task scope and request Review with actual deliverables/evidence. They must not self-complete.
5. Lee inspects and accepts through dashboard **Complete**.
6. Lee explicitly sends results to GitHub Human Review or Blocked. This does not close the GitHub issue. Close only after human acceptance of every required criterion.

Planning intake is not blanket authorization. Report missing approval or dependencies with the native blocker lifecycle. Do not use stale foreground-only launch requirements for ordinary native work.

Dashboard: `http://127.0.0.1:9119/kanban?profile=jeeves`; connection/results: `http://127.0.0.1:9119/jeeves-launch?profile=jeeves`. Do not assume Hermes Desktop uses the same runtime/board without verification.

Board: `%LOCALAPPDATA%\hermes\kanban\boards\landmarksignal\kanban.db`. Read the exact card workspace, not the chat's current directory. Duplicate detection includes archived cards; importing again does not revive archived work. Preserve history and workspace artifacts.
