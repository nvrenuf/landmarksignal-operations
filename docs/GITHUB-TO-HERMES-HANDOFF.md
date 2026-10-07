> Historical report — superseded by [FINAL_REPORT_V1.md](FINAL_REPORT_V1.md).
> Its test counts, readiness claims and execution instructions are not current evidence.

# GitHub-to-Hermes Handoff Implementation

## Target Workflow

```
GitHub Issue (Queued for Jeeves / Todo)
    ↓
Explicit execution authorization (manual)
    ↓
Hermes Kanban task (claim)
    ↓
Jeeves supervised execution
    ↓
Validation (request-review)
    ↓
PR / evidence attached
    ↓
GitHub Human Review (In Progress / Done)
```

## Implementation Rules

### 1. Authorization Gate
- All Kanban claims require GitHub issue ID reference
- Manual approval required before claim
- No auto-dispatch or cron jobs

### 2. Task Linking
- Every Kanban task must reference originating GitHub issue
- GitHub issue URL must be preserved in task comments/attachments
- Task completion updates GitHub issue with PR links

### 3. Duplicate Prevention
- Before claiming, verify no task exists for same GitHub issue
- Use `hermes kanban list` to check existing tasks

### 4. Evidence Tracking
- Completed tasks attach PR URLs to GitHub issues
- Validation results documented in task comments
- Evidence must include: PR link, test results, screenshots

### 5. Human Review Gate
- NEVER auto-mark GitHub issue as "Done"
- Always transition to "In Progress" first
- Lee must approve before "Done"

### 6. Blocked States
- If task blocks: update GitHub issue with blocker description
- Escalate to Lee for resolution
- Do not proceed past blocked state

### 7. Failure Handling
- Task fails → update Kanban task with error
- Mark GitHub issue as "In Progress" (not "Done")
- Document failure in issue comments

## Tools

### kanban-control.py
Python-based execution control with:
- Authorization checks
- Task count enforcement
- GitHub issue validation

### kanban-guard.bat
Windows batch guard for basic operations

## Authorization Command

```bash
# Manual authorization for claiming a task
gh issue view <GITHUB_ISSUE_ID> --repo nvrenuf/landmarksignal-operations
hermes kanban claim --board landmarksignal
```

## Test Case: Issue #1

Target: Document Hermes and DGX baseline
- GitHub Issue: #1
- Execution Order: 10
- Priority: P1
- Status: Todo (ready for handoff)

## Next Steps

1. Claim Issue #1 in Hermes Kanban
2. Execute documentation work
3. Create branch and PR
4. Update GitHub issue with evidence
5. Transition to Human Review

