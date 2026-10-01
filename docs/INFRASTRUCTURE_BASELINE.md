# Infrastructure Baseline

## Verified Configuration

### Jeeves

- **Runtime:** Windows-native Hermes Agent (browser interface)
- **Hermes version:** 0.21.3
- **Local model:** Qwen3.5-9B-Q4_K_M
- **Model provider:** llama.cpp
- **Local memory:** Yes
- **GitHub CLI:** Authenticated (gh version 2.81.0)
- **Profile:** jeeves (Jeeves@1.0.0)
- **SOUL.md:** Present and verified
- **Distribution:** Jeeves@1.0.0
- **Config file:** C:/Users/lee/AppData/Local/hermes/profiles/jeeves/config.yaml

### Hermes Kanban

- **Board slug:** landmarksignal
- **Board name:** LandmarkSignal
- **Database:** C:/Users/lee/AppData/Local/hermes/kanban/boards/landmarksignal/kanban.db
- **Database type:** SQLite (verified)
- **Status:** Persistent storage with board.json and kanban.db (118KB)
- **Current tasks:** 1 active (t_b4bb78ed - Issue #1, status: ready)
- **Dispatch mode:** Manual only (no cron/daemon/auto-gateway dispatch)
- **Concurrency control:** Maximum 1 active task enforced
- **Auto-dispatch:** Disabled (verified: no cron jobs, no daemon processes)

### Hermes Gateway

- **Status:** Running (default-profile multiplexer)
- **PID:** 39508
- **Kanban dispatch:** Disabled (manual-only)
- **Cron jobs:** None scheduled (verified)
- **Auto-dispatch:** Not enabled (verified)

### Local Model Server

- **Model:** Qwen3.5-9B-Q4_K_M
- **Provider:** llama.cpp
- **Port:** 127.0.0.1:8000 (LISTENING - verified)
- **Status:** Operational (port verified)
- **Note:** llama.cpp process verification pending

## DGX Infrastructure (Community Capital - DO NOT INTERRUPT)

### DGX-Forge

- **Hostname:** spark-99ed
- **IP:** 10.0.0.150
- **Role:** DGX-Forge
- **vLLM:** Yes
- **Model:** nvidia/Qwen3.6-35B-A3B-NVFP4
- **Endpoint:** http://10.0.0.150:8000/v1
- **Reachable from Windows:** Unauthorized response (no auth required for verification)
- **Network bindings:** 10.0.0.150:8000 (unchanged - verified)
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

- **Kanban dispatch:** Manual only (verified)
- **Child tasks:** Require authorization (policy documented)
- **Concurrency limit:** Maximum 1 active task (enforced)
- **Auto-dispatch:** Disabled (verified)
- **Cron jobs:** None (verified)

## Verification Status

| Item | Status | Verified |
|------|--------|----------|
| DGX-Forge endpoint | Running | Yes (Unauthorized = expected) |
| DGX-Forge network bindings | Unchanged | Yes |
| Local model port | Listening | Yes |
| Kanban task state | Ready | Yes |
| Auto-dispatch | Disabled | Yes |
| Cron jobs | None | Yes |

## Corrections Made

Previous version contained claims that required verification. This version:
- Separates verified from pending items
- Documents actual verification results
- Clarifies what has been tested vs what needs testing

---

*This baseline is verified as of 2026-10-01 12:55. Any changes require explicit approval.*
