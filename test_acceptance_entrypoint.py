"""Reproduce Hermes's isolated runpy launch without approvals or model calls."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest


class AcceptanceEntrypointTests(unittest.TestCase):
    def test_dependency_activation_precedes_companion_imports(self):
        runner = Path(__file__).resolve().parent / "guarded_jeeves_acceptance.py"
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "hermes/hermes-agent"
            runtime.mkdir(parents=True)
            (runtime / "hermes_bootstrap.py").write_text(
                "import os; os.environ['TEST_DEPENDENCIES_ACTIVE']='yes'\n")
            # Stop at main's bootstrap; never reach approval, a card or a model.
            (runtime / "install_jeeves_policy.py").write_text(
                "import yaml, os\n"
                "assert os.environ.get('TEST_DEPENDENCIES_ACTIVE') == 'yes'\n"
                "def bootstrap(): raise SystemExit(0)\n"
                "def verify_installed(profile): pass\n")
            command = (
                "import os, sys, runpy, importlib.abc, types\n"
                "class DependencyTrap(importlib.abc.MetaPathFinder):\n"
                " def find_spec(self, fullname, path=None, target=None):\n"
                "  if fullname == 'yaml' and os.environ.get('TEST_DEPENDENCIES_ACTIVE') != 'yes':\n"
                "   raise ModuleNotFoundError('yaml dependencies not activated')\n"
                "sys.meta_path.insert(0, DependencyTrap())\n"
                "sys.stdin = types.SimpleNamespace(isatty=lambda: True)\n"
                "runpy.run_path(" + repr(str(runner)) + ",run_name='__main__')\n"
            )
            env = {**os.environ, "LOCALAPPDATA": directory}
            env.pop("TEST_DEPENDENCIES_ACTIVE", None)
            result = subprocess.run([sys.executable, "-I", "-B", "-c", command],
                                    env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)

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
