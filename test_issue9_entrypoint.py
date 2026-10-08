"""Regression: managed runpy must import both root and issue9 companions."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

class EntrypointTests(unittest.TestCase):
    def test_isolated_runpy_resolves_all_companions(self):
        script=Path(__file__).resolve().with_name('test_issue9_workflow.py')
        probe="import runpy,sys; script=sys.argv[1]; sys.argv=[script]; runpy.run_path(script,run_name='__main__')"
        with tempfile.TemporaryDirectory() as folder:
            result=subprocess.run([sys.executable,'-I','-B','-c',probe,str(script)],
                                  cwd=folder,capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('Ran 10 tests',result.stderr)
        self.assertIn('OK',result.stderr)

if __name__=='__main__':unittest.main(verbosity=2)
