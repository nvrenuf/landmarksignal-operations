"""Reproduce Hermes's isolated runpy launch without approvals or model calls."""

from pathlib import Path
import subprocess
import sys
import unittest


class AcceptanceEntrypointTests(unittest.TestCase):
    def test_isolated_runpy_can_import_companion_guard(self):
        runner = Path(__file__).resolve().parent / "guarded_jeeves_acceptance.py"
        command = (
            "import runpy; namespace=runpy.run_path(" + repr(str(runner)) +
            ",run_name='_entrypoint_probe_'); "
            "assert namespace['ExecutionGuard'].__module__ == 'execution_guard_v1_final'"
        )
        result = subprocess.run([sys.executable, "-I", "-B", "-c", command],
                                cwd=runner.parent.parent, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
