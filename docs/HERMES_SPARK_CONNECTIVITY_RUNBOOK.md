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
