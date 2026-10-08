"""Run the focused fixture suite under the existing managed Hermes runtime."""
import os
from pathlib import Path
import sys
if os.name=='nt':
    sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'hermes/hermes-agent'))
    import hermes_bootstrap
sys.path.insert(0,str(Path(__file__).resolve().parent))
import unittest

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromNames([
        'test_github_projects', 'test_github_acceptance', 'test_github_intake', 'test_jeeves_dashboard',
        'test_issue9_workflow', 'test_github_projects_install', 'test_issue9_entrypoint'])
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
