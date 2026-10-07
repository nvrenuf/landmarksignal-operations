# LandmarkSignal Kanban Execution Policy

## Purpose
Define the execution safety and manual control policy for the LandmarkSignal Hermes Kanban board.

## Board Identity
- **Slug:** `landmarksignal`
- **Name:** LandmarkSignal Hermes Operations Board
- **Database:** `C:\Users\lee\AppData\Local\hermes\kanban\boards\landmarksignal\kanban.db`

## Execution Safety Rules

### 1. Manual Dispatch Only
- **NO automatic gateway dispatch**
- **NO cron jobs**
- **NO daemon processes**
- All task claims/dispatches require explicit human authorization

### 2. Single Active Task Limit
- Maximum **1** task in running state at any time
- New tasks blocked until previous task completes
- Exception: Jeeves may override for critical path work (requires explicit approval)

### 3. Authorization Requirements
All Kanban operations require:
- **Claim:** GitHub issue ID reference + manual approval
- **Dispatch:** Manual approval after dry-run review
- **Swarm/Decompose:** GitHub issue approval required

### 4. Child Task Policy
- Child tasks require explicit authorization
- Swarm operations blocked without approval
- Decomposition operations blocked without approval

### 5. Traceability
- Every task must reference originating GitHub issue
- Evidence must be attached to completed tasks
- PRs linked to GitHub issue fields

## Authorized Operations

| Operation | Authorization | Frequency |
|-----------|---------------|-----------|
| `claim` | GitHub issue ID + manual approve | Per task |
| `dispatch` | Manual approve after dry-run | Per sprint |
| `complete` | Manual approve | Per task |
| `request-review` | Manual approve | Per task |

## Blocked Operations

| Operation | Reason |
|-----------|--------|
| `swarm` | Requires GitHub issue approval |
| `decompose` | Requires GitHub issue approval |
| `dispatch --auto` | Not allowed |
| Cron dispatch | Not allowed |

## Tools & Scripts

### kanban-control.py
Python-based execution control with:
- Authorization checks
- Task count enforcement
- GitHub issue validation

### kanban-guard.bat
Windows batch guard for basic operations

## Verification

Before each operation:
```bash
# Check active task count
hermes kanban stats --board landmarksignal

# Verify GitHub issue exists
gh issue view <ID> --repo nvrenuf/landmarksignal-operations

# Review task dependencies
hermes kanban show <TASK_ID> --board landmarksignal
```

## Audit Trail

All operations logged to:
- `kanban.db.task_events`
- Task comments
- GitHub issue comments

## Last Updated
2026-10-01
