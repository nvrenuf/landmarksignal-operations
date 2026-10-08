"""Normal-user read-only installed payload and connection verification."""
import ctypes
import json
import os
from pathlib import Path
import sys
if os.name!='nt' or ctypes.windll.shell32.IsUserAnAdmin():
    raise RuntimeError('Verify using normal Lee, never an administrator')
root=Path(os.environ['LOCALAPPDATA'])/'hermes'
sys.path.insert(0,str(root/'hermes-agent'))
import hermes_bootstrap
source=Path(__file__).resolve().parent
runner=root/'plugins/landmarksignal-launch/dashboard/runner'
sys.path[:0]=[str(runner),str(source)]
import github_projects
import github_queue_intake
import github_handoff_results
from install_github_projects import sha
for module in (github_projects,github_queue_intake,github_handoff_results):
    if Path(module.__file__).resolve().parent!=runner:
        raise RuntimeError('Verification loaded source instead of installed payload')
for entry in json.loads((source/'github_projects_assets.json').read_text()):
    if sha((root/entry['target']).read_bytes())!=entry['new_sha256']:
        raise RuntimeError('Installed checksum differs: '+entry['target'])
print('PASS: all five installed payload hashes and normal-user companion imports')
for selector in github_projects.PROJECTS:
    records=github_queue_intake.read_queue(selector=selector)
    results=github_handoff_results.inspect_results(root,selector)
    print('PASS:',selector,'read-only connection; queued:',len(records),'returnable:',len(results))
print('No import, GitHub mutation, task release, worker launch, or configuration write.')
if '--fixtures' in sys.argv:
    import unittest
    import test_github_projects as fixtures
    if fixtures.intake is not github_queue_intake or fixtures.returns is not github_handoff_results:
        raise RuntimeError('Fixtures did not use installed modules')
    suite=unittest.defaultTestLoader.loadTestsFromNames([
        'test_github_projects.SelectionTests', 'test_github_projects.ProjectImportTests',
        'test_github_projects.ResultTests'])
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():sys.exit(1)
    print('PASS: isolated mutation fixtures exercised the installed intake/results modules.')
