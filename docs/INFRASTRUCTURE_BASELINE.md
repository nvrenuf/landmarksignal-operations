# Infrastructure Baseline

## Verified Configuration

### Jeeves

- **Runtime:** Windows-native Hermes
- **Hermes version:** 0.21.3
- **Local model:** Qwen3.5-9B-Q4_K_M
- **Runtime:** llama.cpp
- **Local memory:** Yes
- **GitHub CLI:** Authenticated

### DGX-Forge

- **Hostname:** spark-99ed
- **IP:** 10.0.0.150
- **Role:** DGX-Forge
- **vLLM:** Yes
- **Model:** nvidia/Qwen3.6-35B-A3B-NVFP4
- **Endpoint:** http://10.0.0.150:8000/v1
- **Reachable from Windows:** Yes
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

---

*This baseline is verified as of 2026-09-30 22:35:28. Any changes require explicit approval.*
