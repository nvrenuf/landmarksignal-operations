> Historical checkpoint: the observations and pending/merged claims below are dated evidence, not current launch instructions. See [current workflow](GITHUB_HERMES_WORKFLOW.md) and [execution policy](KANBAN_EXECUTION_POLICY.md). PRs #20, #23, #24 and #25 have since merged with Lee's approval; the nine-stage Status field and guarded document pilots are complete. Broader dispatcher, intake/specifier and tool-enabled worker coverage remain unverified. Preserve this report for traceability.

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
- **Current tasks:** 1 ready (t_b4bb78ed - Issue #1)
- **Dispatch mode:** Manual only (no cron/daemon/auto-gateway dispatch)
- **Concurrency control:** Task-level locking (per-task claim protection)
- **Auto-dispatch:** Disabled (verified: no cron jobs, no dispatch processes)

### Hermes Gateway

- **Status:** Running (default-profile multiplexer)
- **PID:** 39508
- **Kanban dispatch:** Disabled (manual-only)
- **Cron jobs:** None scheduled (verified)
- **Auto-dispatch:** Not enabled (verified: no dispatch activity in tail)
- **Active Hermes processes:** 6 instances (hermes.exe PIDs: 34512, 40784, 8680, 49512, 71656, 27156)

### Local Model Server

- **Model:** Qwen3.5-9B-Q4_K_M
- **Provider:** llama.cpp
- **Port:** 127.0.0.1:8000 (LISTENING - verified)
- **Process:** llama-server.exe (PID 29980, 92MB RAM)
- **Health check:** GET /health returns {"status":"ok"}
- **Models endpoint:** GET /v1/models returns 404 (expected for llama.cpp)
- **Status:** Operational (read-only health verified)

- **Date:** 2026-10-01 13:10

## DGX Infrastructure (Community Capital - DO NOT INTERRUPT)

### DGX-Forge

- **Hostname:** spark-99ed
- **IP:** 10.0.0.150
- **Role:** DGX-Forge
- **vLLM:** Yes
- **Model:** nvidia/Qwen3.6-35B-A3B-NVFP4
- **Endpoint:** http://10.0.0.150:8000/v1
- **Reachability test:** GET /v1/models returns 401 Unauthorized (expected)
- **Network bindings:** 10.0.0.150:8000 (unchanged - verified via netstat)
- **CCT dependency:** Active
- **Status:** **DO NOT INTERRUPT**

### DGX-Lab

- **Hostname:** spark-6d3e
- **IP:** 10.0.0.161
- **Role:** DGX-Lab
- **vLLM:** Yes
- **Model:** Qwen/Qwen3-Coder-Next-FP8
- **Endpoint:** Currently bound to localhost
- **Reachability from Windows:** No
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

| Control | Status | Evidence |
|---------|--------|----------|
| Kanban dispatch | Manual only | Verified: no cron/daemon processes |
| Per-task duplicate claim | Enforced | Verified: second claim fails with lock error |
| Global one-task-at-a-time | **NOT ENFORCED** | Two different task claim test: both succeeded |
| Child-task authorization | **NOT ENFORCED** | Child task created without approval |
| Auto-dispatch | Disabled | Verified: no cron jobs, no dispatch activity |

## Verification Status

| Item | Status | Verified |
|------|--------|----------|
| DGX-Forge endpoint | Running | Yes (401 = expected) |
| DGX-Forge network bindings | Unchanged | Yes |
| Local model port | Listening | Yes |
| Local model health | OK | Yes (/health returns ok) |
| Local model process | llama-server.exe PID 29980 | Yes |
| Kanban per-task locking | Working | Yes |
| Global concurrency guard | Tested | **No** (two different tasks both claimable) |
| Child-task authorization | Tested | **No** (child task created without approval) |
| Auto-dispatch | Disabled | Yes |

## Time-Dependent Observations (2026-10-01 13:10)

- **Task count:** 1 ready, 1 running (previously 0)
- **PIDs:** llama-server.exe 29980 (92MB), hermes.exe instances 34512, 40784, 8680, 49512, 71656, 27156
- **Port:** 127.0.0.1:8000 LISTENING
- **DGX bindings:** 10.0.0.150:8000 active

## Corrections from Previous Versions

1. **Concurrency guard:** Distinguished per-task locking (verified) from global one-task-at-a-time (NOT enforced)
2. **Child-task authorization:** Marked as NOT ENFORCED - no enforcement mechanism detected
3. **Local model health:** Added read-only health check results
4. **DGX-Forge reachability:** Added actual HTTP response (401 Unauthorized)
5. **Time-dependent facts:** Moved task count, PIDs, and port status to dated observation section
6. **Gateway auto-dispatch:** Verified via runtime behavior (no dispatch activity)

## GitHub Project Workflow

**Status:** GitHub Project #3 Status field currently supports only:
- Todo
- In Progress
- Done

**Nine-stage workflow (Idea, Defined, Sprint Ready, Queued for Jeeves, In Progress, Validation, Human Review, Blocked, Done) is NOT implemented.** Manual mapping used:
- Todo → Defined
- In Progress → Queued/In Progress  
- Done → Human Review/Done

**Issue #1 status:** OPEN with comment added. **NOT in Human Review state** due to Status field limitation.

---

*This baseline is verified as of 2026-10-01 13:10. Any changes require explicit approval.*
