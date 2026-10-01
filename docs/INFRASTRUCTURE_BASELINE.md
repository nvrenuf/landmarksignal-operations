# Infrastructure Baseline

## Verified Configuration

### Jeeves

- **Runtime:** Windows-native Hermes
- **Hermes version:** 0.21.3
- **Local model:** Qwen3.5-9B-Q4_K_M
- **Model provider:** llama.cpp
- **Local memory:** Yes
- **GitHub CLI:** Authenticated (gh version 2.81.0)
- **Profile:** jeeves (Jeeves@1.0.0)
- **SOUL.md:** Present and verified
- **Distribution:** Jeeves@1.0.0
- **Config file:** config.yaml (model: Qwen3.5-9B-Q4_K_M, provider: llamacpp)

### Hermes Kanban

- **Board slug:** landmarksignal
- **Board name:** LandmarkSignal
- **Database:** C:\Users\lee\AppData\Local\hermes\kanban\boards\landmarksignal\kanban.db
- **Database type:** SQLite
- **Status:** Persistent storage with board.json and kanban.db (118KB)
- **Current tasks:** 1 active (t_b4bb78ed - Issue #1)
- **Dispatch mode:** Manual only (no cron/daemon/auto-gateway dispatch)
- **Concurrency control:** Maximum 1 active task enforced

### Hermes Gateway

- **Status:** Running (default-profile multiplexer)
- **PID:** 39508
- **Kanban dispatch:** Disabled (manual-only)
- **Cron jobs:** None scheduled
- **Auto-dispatch:** Not enabled

### Local Model Server

- **Model:** Qwen3.5-9B-Q4_K_M
- **Provider:** llama.cpp
- **Status:** Operational (verified via config)
- **Note:** Port verification pending (netstat check recommended)

## DGX Infrastructure (Community Capital - DO NOT INTERRUPT)

### DGX-Forge

- **Hostname:** spark-99ed
- **IP:** 10.0.0.150
- **Role:** DGX-Forge
- **vLLM:** Yes
- **Model:** nvidia/Qwen3.6-35B-A3B-NVFP4
- **Endpoint:** http://10.0.0.150:8000/v1
- **Reachable from Windows:** Yes (verified via Hermes config)
- **CCT dependency:** Active
- **Status:** **DO NOT INTERRUPT**

### DGX-Lab

- **Hostname:** spark-6d3e
- **IP:** 10.0.0.161
- **Role:** DGX-Lab
- **vLLM:** Yes
- **Model:** Qwen/Qwen3-Coder-Next-FP8
- **Endpoint:** Currently bound to localhost
- **Reachable from Windows:** No
- **Status:** DO NOT RECONFIGURE WITHOUT APPROVAL

## Policy

> **Existing Community Capital DGX services are production dependencies. LandmarkSignal infrastructure work must be additive. Do not restart, rebind, replace, remove, or interrupt an existing CCT service without explicit approval.**

## Network & Access

- **NVIDIA Sync:** Currently provides the Spark cluster/network configuration
- **Ray/NCCL distributed inference:** Not currently active
- **Future distributed inference:** May be added behind stable logical model endpoints
- **Model gateway/proxy:** NGINX is the preferred future implementation
- **Mac access to CCT model services:** Must remain untouched

## Execution Safety

- **Kanban dispatch:** Manual only
- **Child tasks:** Require authorization
- **Concurrency limit:** Maximum 1 active task
- **Auto-dispatch:** Disabled
- **Cron jobs:** None

---

*This baseline is verified as of 2026-10-01 12:41. Any changes require explicit approval.*
