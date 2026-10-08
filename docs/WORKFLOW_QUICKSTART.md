# GitHub-to-Hermes Operator Quickstart

## Overview
This workflow connects GitHub issues to Hermes Agent workers via a Kanban board, enabling structured sprint-based execution with human oversight.

**Source Issue:** https://github.com/nvrenuf/landmarksignal-operations/issues/30

## 1. Planning Record: GitHub Project #3
All intake issues live in **GitHub Project #3** (https://github.com/nvrenuf/projects/3). This is the single source of truth for queued work.

## 2. Import Queued Work
Lee clicks **"Import queued work"** to import issues marked with the **"Queued for Jeeves"** status option in GitHub Project #3. The importer:

- Creates unassigned Triage cards
- Preserves source requirements and recorded dependencies

## 3. Triage → Ready → Auto-Promotion

- **Triaged**: Hermes specifies and decomposes work as needed. To-do cards may auto-promote when dependencies are satisfied.
- **Ready**: Tasks are eligible to launch work.
- **Auto-promotion**: Status transitions based on dependency satisfaction and Hermes decomposition.

## 4. Worker Output to Review
Workers call `kanban_request_review` and **stop at Review**:

- Moves task to `review` column
- Includes `summary` and `metadata` for handoff
- **Never calls `kanban_complete`**

## 5. Lee Accepts Through Dashboard
Lee accepts work through the dashboard's **Complete** action. Workers must not call `kanban_complete`, including after approval.

## 6. Send Results to GitHub Human Review
Lee clicks **Send results to GitHub Human Review** to return execution evidence. This does not complete or close the GitHub issue.

## 7. Human Control of Priority/Order/Sprint

- **Priority**: GitHub Project field controlled by Lee
- **Execution Order**: GitHub Project field controlled by Lee
- **Sprint**: GitHub Project field controlled by Lee
- Lee authorizes merges/deployments; **Jeeves does not grant that approval**

## Key Rules

- Work scope depends on each task's authorization; permitted work varies by task
- Hermes Kanban coordinates work; workers use the tools permitted by the task's scope.
- Lee retains final approval authority via dashboard Complete action
- Evidence and artifacts must be verified before handoff
