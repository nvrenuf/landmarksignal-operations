"""Verify policy denial, workspace boundaries and safe configuration edits."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

import yaml

from configure_jeeves_v1 import prepare
from execution_guard_v1_final import ExecutionGuard, HAS_WIN32EVENT
from install_jeeves_policy import disable_review_dispatch, install
from landmarksignal_policy import SCOPE_MODULE, decide


class PolicyTests(unittest.TestCase):
    def test_unowned_mutations_are_denied(self):
        for name in ("terminal", "execute_code", "write_file", "delegate_task", "kanban_create",
                     "kanban_unblock", "kanban_complete", "unknown_future_tool"):
            self.assertEqual(decide(name, {})["action"], "block")

    def test_planning_reads_remain_available(self):
        for name in ("read_file", "search_files", "web_search", "web_extract"):
            self.assertIsNone(decide(name, {}))

    def test_expired_or_wrong_issue_scope_does_not_grant_execution(self):
        invalid = SimpleNamespace(guard=SimpleNamespace(_acquired=False), acceptance=False)
        with patch.dict(sys.modules, {SCOPE_MODULE: invalid}):
            self.assertEqual(decide("write_file", {})["action"], "block")

    def test_review_gate_preserves_model_and_rejects_explicit_conflict(self):
        original = prepare(b"# original\r\nmodel:\r\n  default: keep-model\r\n")
        updated = disable_review_dispatch(original)
        self.assertEqual(yaml.safe_load(updated)["model"], {"default": "keep-model"})
        self.assertTrue(updated.startswith(b"# original\r\nmodel:\r\n  default: keep-model\r\n"))
        self.assertIs(disable_review_dispatch(updated), updated)
        conflicting = original.replace(b"kanban:\r\n", b"kanban:\r\n  review_dispatch: true\r\n")
        with self.assertRaises(RuntimeError):
            disable_review_dispatch(conflicting)

    def test_install_preserves_config_and_existing_plugins_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            original = prepare(b"# preserve\nmodel: {default: existing}\n")
            path = profile / "config.yaml"
            path.write_bytes(original)
            other = profile / "plugins/other-plugin/data.txt"
            other.parent.mkdir(parents=True)
            other.write_text("keep this")
            with patch("install_jeeves_policy.verify_installed"):
                install(profile)
                installed = path.read_bytes()
                install(profile)
            self.assertEqual(path.read_bytes(), installed)
            self.assertEqual(yaml.safe_load(installed)["model"], {"default": "existing"})
            self.assertEqual(other.read_text(), "keep this")
            backups = list(profile.glob("config.pre-policy-*.yaml"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), original)

    def test_obsolete_claim_and_token_dispatch_cannot_invoke_hermes(self):
        script = Path(__file__).parent / "kanban-control.py"
        for args in (["claim", "19"], ["dispatch"], ["anything", "dispatch"]):
            result = subprocess.run([sys.executable, str(script), *args],
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 2)
            self.assertIn("BLOCKED", result.stderr)


@unittest.skipUnless(HAS_WIN32EVENT, "Native Windows mutex required")
class OwnedPolicyTests(unittest.TestCase):
    def test_owned_acceptance_denies_tools_and_observation_cannot_release_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            guard = ExecutionGuard("19", "test", state_dir=directory,
                                   mutex_name="PolicyTest-" + uuid.uuid4().hex, timeout=0)
            guard.acquire()
            scope = SimpleNamespace(guard=guard, acceptance=True, workspace=directory,
                                    issue_url="https://github.com/nvrenuf/landmarksignal-operations/issues/19")
            try:
                with patch.dict(sys.modules, {SCOPE_MODULE: scope}):
                    calls = []
                    worker = threading.Thread(target=lambda: calls.append(decide("delegate_task", {})))
                    worker.start()
                    worker.join(3)
                    self.assertFalse(worker.is_alive())
                    self.assertEqual(calls[0]["action"], "block")
                    self.assertTrue(guard._acquired)
            finally:
                self.assertTrue(guard.release())

    def test_owned_file_scope_rejects_escape_and_wrong_issue(self):
        with tempfile.TemporaryDirectory() as directory:
            guard = ExecutionGuard("19", "test", state_dir=directory,
                                   mutex_name="PolicyTest-" + uuid.uuid4().hex, timeout=0)
            guard.acquire()
            scope = SimpleNamespace(guard=guard, acceptance=False, workspace=directory,
                                    issue_url="https://github.com/nvrenuf/landmarksignal-operations/issues/19")
            try:
                with patch.dict(sys.modules, {SCOPE_MODULE: scope}):
                    self.assertIsNone(decide("read_file", {"path": "notes.txt"}))
                    self.assertEqual(decide("read_file", {"path": "../outside.txt"})["action"], "block")
                    self.assertEqual(decide("delegate_task", {})["action"], "block")
                    scope.issue_url = scope.issue_url.replace("/19", "/18")
                    self.assertEqual(decide("write_file", {"path": "notes.txt"})["action"], "block")
            finally:
                self.assertTrue(guard.release())


if __name__ == "__main__":
    unittest.main(verbosity=2)
