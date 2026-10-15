# October 15, 2026 Jeeves recovery checkpoint — verified live reply

This is an operational update to [the canonical two-Spark connectivity runbook](HERMES_SPARK_CONNECTIVITY_RUNBOOK.md). It supersedes the older statement in that runbook that Jeeves is still using the broken Forge custom provider. The long-term Forge migration remains pending.

## Verified working local baseline

On October 15 the October 14 model block was restored **only** in `%LOCALAPPDATA%\hermes\profiles\jeeves\config.yaml`; the rest of the profile/board was preserved. `hermes -p jeeves config get model --json` returned `default=Qwen3.5-9B-Q4_K_M`, `provider=llamacpp`, `base_url=http://127.0.0.1:18434/v1`, `api_mode=chat_completions`, `reasoning_effort=high`. The TCP check to `127.0.0.1:18434` passed. A new Jeeves chat returned `ONLINE - Model: Qwen3.5-9B-Q4_K_M`. This proves live local inference, **not** reboot persistence, startup tasks, or Forge access.

The original recovery source was `config.yaml.bak-20261014-173504`. A separate `config.yaml.before-recovery-<timestamp>` backup was made before the targeted change. Do not blindly restore the whole old profile or overwrite live Kanban data.

## Architecture and remaining work

- DGX-Forge `10.0.0.150:8000/v1` serves `nvidia/Qwen3.6-35B-A3B-NVFP4`, protected by API authentication. The broken cutover changed the URL/provider but retained Qwen3.5 model ID; HTTP 401 remains unresolved. Forge belongs to shared existing CCT/Gloria infrastructure and must not be restarted or reconfigured casually.
- DGX-Lab `10.0.0.161`: separate Qwen3-Coder-Next model. Local tunnel on `127.0.0.1:8001` is the Lab path, **not** the Forge path. WSL `LandmarkSignal-Ubuntu` and `NCS` are separate workspaces.
- Existing Windows SSH alias `CCT-Forge` points to `spark-99ed.local`; hostname resolution was broken. NVIDIA Sync private key ACLs were rejected by Windows OpenSSH. Password SSH to `cct-lee@10.0.0.150` worked.

## Durable recovery and startup requirements

1. Immediately take a private local checkpoint: selected config files, plugin versions/hashes, scheduled-task definitions, model settings, and a consistent SQLite online backup of the native board. Treat configs as secret-bearing and keep out of GitHub.
2. Inventory existing Windows Scheduled Tasks and SSH tunnel owning processes before installing/replacing any service. Avoid duplicate tunnels. Determine whether persistence is at logon/startup, which principal runs it, and whether missed starts/restarts are configured.
3. Build a verified restore utility that restores **only** selected model configuration in a controlled fashion; restore Kanban DB only after explicit approval and when writers are stopped. Test restoration before deleting checkpoints.
4. Use service supervisors or existing Scheduled Tasks with dependency-aware start/retry/health tests for the local model, Lab tunnel, Jeeves gateway, standalone dashboard. Check actual inference and exact model ID, not only open ports. If a Forge route is persistent, preserve auth and owner boundaries.
5. Complete authenticated Forge test **independently**, create another checkpoint, switch Jeeves to exact Forge model ID only after authenticated inference passes, and keep local llama.cpp model as a deliberately documented fallback. Do not print tokens or disable authentication.
6. After every successful change update this file and the canonical runbook with time, tested result, backup location (never secret content), explicit restoration procedure and owners.

Checkpoint/inspection helper package was delivered to operator on October 15; **not yet executed** on the user's laptop. No startup tasks were created or changed by this documentation.
