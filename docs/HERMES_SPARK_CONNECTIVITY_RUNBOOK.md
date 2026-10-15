# Hermes + two DGX Sparks: canonical topology and recovery

Updated 2026-10-15. This is the **current operator reference** for connectivity and the October 15 Jeeves model incident. Read with [Hermes folder map](HERMES_FOLDER_MAP.md), [GitHub/Hermes workflow](GITHUB_HERMES_WORKFLOW.md), and [execution policy](KANBAN_EXECUTION_POLICY.md). Historical baselines are dated evidence, not live instructions.

## Components and ownership

| System | Role | Connection and known model |
|---|---|---|
| Windows 11 `jc-laptop-x17` | Native Hermes / Jeeves, browser, GitHub Kanban launch | profile `jeeves` in `%LOCALAPPDATA%\hermes\profiles\jeeves`; dashboard `http://127.0.0.1:9119/jeeves-launch?profile=jeeves` |
| WSL `LandmarkSignal-Ubuntu` | LandmarkSignal isolated Linux workspace | no `~/.ssh/config` observed October 15; not the Windows Jeeves config owner |
| WSL `NCS` | NCS isolated Linux workspace | no `~/.ssh/config` observed October 15; do not alter to fix Jeeves |
| DGX-Forge `spark-99ed` | Existing CCT model service, prospective Jeeves reasoning backend | `10.0.0.150:8000/v1`, `nvidia/Qwen3.6-35B-A3B-NVFP4`, Docker `gloria-vllm` / vLLM 0.28.0; authentication required (401 without valid token) |
| DGX-Lab `spark-6d3e` | Lab/coding/evaluation backend | `10.0.0.161`; Windows SSH tunnel `127.0.0.1:8001` to Lab port 8000; `Qwen/Qwen3-Coder-Next-FP8` |
| Local Windows model | Prior Jeeves fallback/known-good | `Qwen3.5-9B-Q4_K_M`; latest October 14 checkpoint at `127.0.0.1:18434/v1`, NOT the Forge model |

These are separate endpoints. **Port 8001 is the Lab coding-model tunnel, not the Forge reasoning endpoint.** WSL networking may show Windows/WSL listeners in both distributions; that is not evidence of two distinct tunnels. A `401` on Forge means an authentication requirement, not necessarily a service outage. `hermes doctor` checks local setup but does not prove that custom endpoint credentials are valid.

## SSH configuration

Windows `%USERPROFILE%\.ssh\config` includes `C:\Users\lee\AppData\Local\NVIDIA Corporation\Sync\config\ssh_config`. There: `Host CCT-Forge`, `HostName spark-99ed.local`, `User cct-lee`, NVIDIA Sync `nvsync.key`. October 15 `.local` name resolution failed. Password SSH to `cct-lee@10.0.0.150` succeeded. Windows OpenSSH rejected `nvsync.key` due to an overly permissive ACL granting `CodexSandboxUsers`; remediate the ACL in a separately scoped change, preserving NVIDIA Sync access. Do not publish the private key or secrets.

Lab key path previously used: `%USERPROFILE%\.ssh\cct_lab_tunnel_ed25519`. Confirm the persistent tunnel task before changing it.

## October 15 incident: precise cause and next move

- Jeeves currently has `provider=custom`, `base_url=http://10.0.0.150:8000/v1`, `model.default=Qwen3.5-9B-Q4_K_M`, `api_mode=chat_completions`, `reasoning_effort=high`.
- Forge **actually serves** `nvidia/Qwen3.6-35B-A3B-NVFP4`, and `/v1/models` responds `401 Unauthorized` without appropriate credentials.
- Therefore the partially completed Forge cutover has **both a wrong model ID and an unresolved credential path**. The native Jeeves gateway and dashboard can remain healthy while model calls fail.
- October 14 known-good checkpoint had Jeeves on local `Qwen3.5-9B-Q4_K_M` via `127.0.0.1:18434/v1`, Forge healthy, and Lab tunnel returning `Qwen/Qwen3-Coder-Next-FP8`.
- **Immediate recovery:** use the pre-cutover backed-up Jeeves model settings to restore only the local model provider/base URL/model; do not overwrite other profile settings. Verify the local endpoint and one Jeeves response. Do not guess the backup filename or the local API credential. If that backup is unavailable, use read-only config inspection and obtain the exact previous local auth settings before any change.
- **Planned Forge migration:** inspect the existing Forge service's authentication configuration without printing secrets; use the approved existing credential in Jeeves, verify `/v1/models` through the same authorization mechanism, then set the exact Forge model ID. Do not disable Forge auth, replace the container, restart Forge, or modify CCT/Mac/Gloria users.
- Do not repoint Jeeves to `127.0.0.1:8001`: that is Lab/coding. Do not run `hermes setup` or `doctor --fix` as an incident-wide reset.

## Startup/recovery design to implement (not yet claimed deployed)

1. **Persist** each independent service at its owner: Forge vLLM via existing approved Docker restart policy/systemd; Lab vLLM likewise; Windows Lab SSH tunnel using existing Task Scheduler task; local fallback model using its existing service/task; Jeeves gateway via its existing Hermes service/task; standalone dashboard separately.
2. **Dependency-aware tests** after each restart: TCP + authenticated model API + exact model ID + a minimal inference call, not just port-open or `doctor`.
3. **Single read-only Windows health script** checks the four layers: Forge, Lab tunnel, local fallback, Hermes gateway/dashboard; emits a concise green/yellow/red status and redacts secrets.
4. **Change control**: explicit configuration backup and rollback before endpoint/model switches. No secrets in GitHub. No automatic failover between company-owned and NCS-owned paths without authorization.
5. **CI/runbook**: keep this doc current after *each* successful change, with date, exact model ID, endpoint, ownership, persistence task name and approved rollback. GitHub and installed Hermes runtime are separate copies.

## Workflow and safety boundaries

GitHub Project #3 and the approved Project #4 selector feed the **already implemented** Jeeves Launch button, which imports queued work into native Kanban Triage. The Kanban board is `%LOCALAPPDATA%\hermes\kanban\boards\landmarksignal\kanban.db`. Import, native execution, review and GitHub result return are distinct. In particular, To-do is not proof of approval or execution; Ready may automatically dispatch. The current planning-only approval gate is not fully enforced; review [execution policy](KANBAN_EXECUTION_POLICY.md) before dispatching new work.

**Non-negotiable:** Both Sparks support existing CCT and other users. Preserve running Forge services, Lab services, NCS/Gloria, Mac access, existing GitHub/Local board data, and the user's explicit priority/review authority. Perform minimally scoped, reversible changes only.


## October 15 evening update — verified after the initial incident

This section supersedes the earlier *incident-state* description of an incomplete Forge cutover above. The earlier entries remain as a dated troubleshooting record, not the current configuration.

### Model connectivity and profiles

| Role | Verified endpoint or configuration | Evidence / limitation |
|---|---|---|
| Windows `jeeves` orchestrator | `custom`, `chat_completions`, `nvidia/Qwen3.6-35B-A3B-NVFP4`, `http://10.0.0.150:8000/v1`; reasoning effort configured `high` | Native `hermes -p jeeves model` wizard authenticated to Forge, detected the model and saved custom provider named `DGX-Forge Qwen3.6`; Jeeves then responded and performed read-only GitHub Project #4 inspection. Do not treat the configured reasoning value alone as proof of effective inference behavior. |
| Windows `default` local fallback | `Qwen3.5-9B-Q4_K_M` | `hermes profile list` reported running; don't disable until rollback and startup tested. |
| DGX-Lab coding backend | `http://127.0.0.1:8001/v1/models` via existing Windows SSH tunnel; `Qwen/Qwen3-Coder-Next-FP8` | PowerShell `Invoke-RestMethod` returned the exact ID on October 15. **This proves endpoint/model discovery, not that a distinct Hermes coding-worker profile exists or inference/tool calling has been tested.** |

The active Windows Hermes profile list reported **only `default` and `jeeves`**, both gateways running. Gloria and other environments must not be assumed to be Windows profiles.

### Model credential handling and gateway

- Forge without Authorization returned HTTP 401; using the existing Forge container credential via Windows PowerShell returned authenticated model discovery. A Windows User-level `FORGE_VLLM_API_KEY` environment variable was created without putting the literal key into GitHub.
- Initial manual `model.key_env` configuration produced HTTP 401 in browser sessions. Windows User environment had the key while the then-current PowerShell Process environment did not.
- The gateway launch file `%LOCALAPPDATA%\\hermes\\gateway-service\\Hermes_Gateway.vbs` was edited to copy the user environment value into the child process. This alone was **not proven sufficient**: HTTP 401 persisted afterward. Keep the original timestamped backup and review the change during reliability hardening instead of assuming a detached launcher restart worked.
- The **native** `hermes -p jeeves model` wizard successfully authenticated to Forge and saved the custom provider. This is the confirmed successful setup path for this installation (Hermes Web Dashboard screenshot displayed v0.21.7). Avoid duplicative provider changes, printing credentials or reconfiguring the shared Forge container.

### Current GitHub/Kanban behavior — do not assume dispatch

- GitHub Project #4 `Hermes Optimization` uses six statuses. Existing `Todo` single-select option was renamed `Backlog` preserving its option ID and other options; Issues #43–#49 remained in Backlog with P0/P1/P2 and execution order 1–6.
- Issue #37 `OPTIMIZE: Verify effective Hermes settings and establish a lean baseline` was present in Project #4 and, at the time of operator review, appeared queued for Jeeves. The launcher import returned **0 imported, 1 already linked**, resolving to existing native card `t_3aaad718` in `todo`. The card explicitly states intake authorizes planning only and does not approve execution. Reconcile any discrepant GitHub Status using a live field read before assuming it is queued.
- The Kanban configuration read via `hermes -p jeeves config get kanban --json` reported `dispatch_in_gateway=false`, `review_dispatch=false`, `auto_decompose=false`, `orchestrator_profile=""`, `default_assignee=""`, `dispatch_profiles=null`, `max_in_progress=1`, `max_in_progress_per_profile=1`, `max_spawn=1`. This supports a conservative/manual setup but **does not by itself prove the native Ready transition cannot dispatch**. Check actual worker ownership before execution.
- The imported #37 card showed assignee `default`, model `profile default`, priority `0`, not Jeeves/Forge. **Do not send the card to Ready to test Forge routing until the worker assignment/model and approval gate are confirmed.**

### Next authorized steps (not yet deployed)

1. Keep local 9B fallback available and verify a repeatable Forge gateway restart/credential persistence, without restarting shared DGX services.
2. Test authenticated Lab coding inference/tool calls and establish its Hermes worker/profile route separately from the currently working tunnel.
3. Review #37 Kanban assignment and GitHub intake settings, establish explicit Jeeves orchestration and constrained worker profiles, with `dispatch_in_gateway=false` until actual dispatch gates are verified.
4. Implement issues #44–#49 under Project #4, starting with tested backups and recovery, and independent monitoring.
5. Inspect the current launcher for hardcoded `Todo` assumptions following the Project #4 rename, but do not modify runtime code without a scoped test.

**Secrets policy:** No API keys, raw `.env` contents, credential-bearing configs, databases, or private SSH keys in repository evidence.
