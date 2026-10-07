> Historical checkpoint: the observations and pending/merged claims below are dated evidence, not current launch instructions. See [current workflow](GITHUB_HERMES_WORKFLOW.md) and [execution policy](KANBAN_EXECUTION_POLICY.md). PRs #20, #23, #24 and #25 have since merged with Lee's approval; the nine-stage Status field and guarded document pilots are complete. Broader dispatcher, intake/specifier and tool-enabled worker coverage remain unverified. Preserve this report for traceability.

# LandmarkSignal Safety Requirements - Issue #14

## Issue #14: Configure Hermes Agent execution safety and concurrency policy

**Status:** OPEN
**Execution Order:** 100
**Priority:** P1

## Safety Requirements Identified

### 1. Global One-Task-at-a-Time Concurrency Guard

**Current Status:** NOT ENFORCED

**Test Evidence:**
- Test: Attempted to claim two different tasks (t_b4bb78ed and t_f50dd28b) simultaneously
- Result: Both claims succeeded
- Finding: No global concurrency guard exists

**Requirement:** Implement a mechanism to ensure only one LandmarkSignal task executes at a time across the entire system.

**Implementation Options:**
- Global semaphore in Hermes configuration
- Shared lock file at kanban root level
- Gateway-level rate limiting for kanban dispatch
- Cron-based serialization of task claims

**Risk:** Without this guard, multiple tasks can execute concurrently, violating the "one active task" policy.

### 2. Child-Task Authorization Enforcement

**Current Status:** NOT ENFORCED

**Test Evidence:**
- Test: Created child task with `hermes kanban create --parent t_b4bb78ed`
- Result: Succeeded without authorization
- Finding: No authorization mechanism prevents child task creation

**Requirement:** Implement explicit authorization check before allowing child task creation.

**Implementation Options:**
- Require approval flag (--authorized flag)
- Integrate with GitHub issue approval workflow
- Add manual confirmation step in kanban-control.py
- Block swarm/decompose operations by default

**Risk:** Unauthorized child tasks can spawn unapproved workloads, expanding scope beyond approved boundaries.

### 3. Automatic Dispatch Prevention

**Current Status:** VERIFIED AS DISABLED

**Evidence:**
- No cron jobs scheduled
- No dispatch processes running
- Gateway running but not auto-dispatching

**Requirement:** Maintain this state by:
- Blocking any cron job creation for kanban dispatch
- Monitoring for unauthorized dispatch processes
- Alerting on any auto-dispatch configuration changes

**Implementation:**
- Add monitoring script to check for cron jobs
- Add process monitoring for dispatch-related activity
- Document the policy clearly in execution contract

## Safety Controls Required Before Sprint Authorization

| Control | Current | Required | Status |
|---------|---------|----------|--------|
| Global concurrency guard | Not enforced | Enforced | **BLOCKING** |
| Child-task authorization | Not enforced | Enforced | **BLOCKING** |
| Auto-dispatch prevention | Disabled | Maintained | ✓ |

## Acceptance Criteria for Issue #14

- [ ] Global concurrency guard implemented and tested
- [ ] Child-task authorization enforced (block unapproved creation)
- [ ] Auto-dispatch monitoring established
- [ ] Safety controls documented in PR
- [ ] Lee approval obtained

## Link to Infrastructure Baseline

The current state is documented in `docs/INFRASTRUCTURE_BASELINE.md`:
- Section: "Execution Safety"
- Table: Shows "NOT ENFORCED" status for both controls
- Date: 2026-10-01 13:10

## Next Steps

1. Implement global concurrency guard
2. Implement child-task authorization
3. Test both controls with negative tests
4. Document implementation in PR
5. Update INFRASTRUCTURE_BASELINE.md
6. Obtain Lee approval
7. Mark Issue #14 as Sprint Ready

---
*Created: 2026-10-01 13:15*
*PR #18 ready for review (commit 08b4f0f)*
