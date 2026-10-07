# Execution approval and safety

Follow current repository `docs/KANBAN_EXECUTION_POLICY.md` and `docs/JEEVES_EXECUTION_CONTRACT.md`.

Keep gateway dispatch, automatic review dispatch and unattended approval disabled. Maintain one participating guarded execution at a time. Do not interpret Manual orchestration as disabling all worker/promotion routes. Do not alter unrelated services or scheduled tasks.

Installed agent hooks deny unowned shell/task mutations/delegation. Model-facing tools may not forge approval or create an owned scope. Dashboard/native auxiliary endpoints require their own verified guarded entry; hook installation alone is not coverage of those endpoints.

Keep approved issue/task/workspace/source snapshot fixed through the work lifetime. Use only the reviewed guarded entry, preserve unrelated cards and fail closed on unavailable native locking. Never acquire a mutex in a command that exits and assume later commands remain protected. Never release ownership from another thread/process or displace a live owner using metadata expiry.

Require applicable distinct human approvals for child creation and child execution; parent approval is insufficient. Current document tasks permit neither children nor tools. Do not enable decomposition, spawn bots or assign a worker to work around a blocked task.

Permit normal promotion to Ready, but require Lee's exact-scope approval at the guarded launch boundary before work starts. Verify every applicable automatic dispatch path is disabled and demonstrate unapproved Ready cards remain idle. The completed document pilots used native blocked events as sticky holds; preserve that evidence without treating those holds as a target requirement. Returning completed output to Review belongs to the approved run. Lee alone accepts and releases completion. Preserve run evidence and record amendments separately.

Ordinary dispatcher supervision, tool-enabled work, cross-session enforcement, same-user tamper resistance, general scheduling and startup recovery remain unverified. Do not claim globally enforced safety outside participating accepted routes.
