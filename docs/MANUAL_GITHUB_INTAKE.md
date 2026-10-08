# Manual GitHub queue intake

Current intake behavior after merged PRs #28/#29. Use the [full workflow](GITHUB_HERMES_WORKFLOW.md) for native execution and human acceptance.

## Operator action

1. Select work in nvrenuf [Project #3](https://github.com/nvrenuf/projects/3) using the **Queued for Jeeves** Status. Review the whole eligible batch.
2. Open [Jeeves Launch](http://127.0.0.1:9119/jeeves-launch?profile=jeeves) and click **Import queued work**.
3. Read created/existing/skipped results, then follow imported cards on the LandmarkSignal Kanban. Intake creates unassigned Triage cards. Native preparation can later reach Ready and launch workers; intake itself does not call a model or launch a worker.
4. Inspect actual outputs at Review, accept through Complete, then explicitly return results to GitHub using the results panel.

The importer reads all Project pages and eligible open issues, excluding archived Project items, drafts, PRs and closed issues. It preserves source URL/body/update/hash, Project/item/issue identity and recorded GitHub blockers in a separate source snapshot. New snapshots also retain Priority, Execution Order and Sprint fields; it does not change those GitHub values. GitHub blockers are source facts, not automatically mapped native dependency cards or edges.

## Repeats and archived cards

Stable Project/issue identity prevents duplicate intake. Existing linked cards, including archived ones, are reported without resetting or relaunching them. Changed source text is not a new execution approval. Multiple source-linked cards or conflicting orphaned snapshots are reported for review. The clean board does not erase these links: importing Issue #9 again will not revive its archived card.

No GitHub status, authorization, Priority, Execution Order or Sprint is written by import. Results return is a separate explicit action. Intake authorizes planning only; a guaranteed approval stop before native dispatch is still absent. Do not treat Ready as an idle holding column.

## Installed implementation and evidence

The existing integration is installed and was exercised for Issues #9 and #30. Each import serializes participating integration actions through the existing mutex, reads dependencies before board writes, backs up the board, creates native Triage cards in one transaction and verifies pre-existing task rows are preserved. It does not initialize another board, assign tasks, approve children or change infrastructure.

Use [setup_issue9_workflow.ps1](../setup_issue9_workflow.ps1) only for a reviewed compatible maintenance need. Lee's current installation is already verified; merging documentation requires no reinstall. Older intake-only and foreground/read-boundary repair installers remain historical and should not be rerun against the combined payload. See [folder map](HERMES_FOLDER_MAP.md) and [checkpoint](HERMES_WORKFLOW_CHECKPOINT.md).
