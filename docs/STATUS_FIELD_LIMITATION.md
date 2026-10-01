# Status Field Configuration Status

## Current State
The GitHub Project #3 Status field has the following options:
- Todo
- In Progress  
- Done

## Limitation
The GitHub CLI (`gh`) does not support updating single-select field options via command line.
This requires manual update via GitHub UI.

## Workaround
For this assignment, we will use "Todo" as a proxy for "Defined" status.
Issue #1 (our test issue) will be moved to "In Progress" to represent "Queued for Jeeves".

## Recommended Action
Update Status field options via GitHub UI:
1. Go to GitHub Project #3
2. Click "Configure" → "Status"
3. Add options: Idea, Defined, Sprint Ready, Queued for Jeeves, Validation, Human Review, Blocked
4. Rename "Todo" to "Defined" (if desired)
5. Keep "In Progress" and "Done"

## Next Steps
Proceed with Phase Three using current Status values with the following mapping:
- Todo → Defined
- In Progress → Queued for Jeeves / In Progress
- Done → Human Review / Done

This mapping is documented and will be updated when the field options are manually corrected.
