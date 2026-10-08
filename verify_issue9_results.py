"""Read-only results load using the normal Windows dashboard account."""
import os
from pathlib import Path
import sys
root=Path(os.environ['LOCALAPPDATA'])/'hermes'
sys.path.insert(0,str(root/'plugins/landmarksignal-launch/dashboard/runner'))
from github_handoff_results import inspect_results
results=inspect_results(root)
print('PASS: normal-account installed results module loads; results:',len(results))
for result in results:print(result['task_id'],result['status'],result['issue_url'])
print('No Kanban or GitHub records changed')
