# BOT_ROSTER_DRAFT.md

## Overview

This document outlines the proposed Bot Roster for the LandmarkSignal (LMS) Operations framework. All five agents below are currently in **PLANNED** status. No bots have been created, validated, deployed, or assigned active permissions. This roster defines the intended separation of duties and the strict approval boundaries required to prevent unauthorized system modifications or infrastructure access.

### Proposed Bot Roster

| Name | Responsibility | Boundary | Approval Requirement |
| :--- | :--- | :--- | :--- |
| **Argus** | Lead domain oversight for LandmarkSignal operations and strategic alignment. | Cannot initiate code writes, security scans, or research tasks autonomously. | Human approval required for all strategic directives and high-priority task initiation. |
| **LMS-Coder** | Drafts code changes, refactors, and generates implementation logic based on approved specs. | Cannot merge PRs, deploy to production, or execute infrastructure commands. | Requires human review and explicit merge approval before any code is committed to main. |
| **LMS-Security** | Reviews proposed code and configurations for vulnerabilities, risks, and compliance gaps. | Cannot apply security patches, rotate credentials, or access infrastructure directly. | Requires human sign-off on any security remediation plan before execution. |
| **LMS-Reviewer** | Independently validates deliverables, logic, and documentation against approved standards. | May use explicitly approved read-only tools; cannot modify source files or alter configurations. | Requires human confirmation before a deliverable is marked as "Ready for Deployment." |
| **LMS-Research** | Researches approved topics, gathers data, and synthesizes findings into actionable briefs. | Cannot access private databases, execute privileged commands, or modify system settings. | Requires human validation of research scope and data sources before synthesis begins. |

## Operational Constraints

The coordination of these agents is managed by Jeeves. However, Jeeves acts solely as a workflow orchestrator and does not possess deployment authority. Lee has final priority and approval authority. ChatGPT advises on priorities and scope; Jeeves coordinates approved work.

**Zero-Trust Enforcement:**
No worker agent is authorized to approve its own tasks. Furthermore, no agent is permitted to deploy updates, merge pull requests, start child processes, change credentials, or access underlying infrastructure without explicit, scoped human approval. This ensures that all automated actions remain within strictly defined, audited boundaries.

**Pre-Deployment Requirements:**
Before any bot in this roster is instantiated, the following must be configured and validated:
1.  **Profiles:** Unique, isolated Hermes profiles for each agent.
2.  **Credentials:** Scoped API keys and secrets with minimal necessary permissions.
3.  **Allowed Tools:** Explicitly approved Hermes tools for each role, with their availability and permissions verified before deployment.
4.  **Workspaces:** Dedicated repositories and scratch directories.

This document serves as the blueprint for the upcoming deployment phase. No bots are currently active, and no commands should be executed based on this draft.
