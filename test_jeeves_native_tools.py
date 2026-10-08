"""Verify native lifecycle access and narrowly retained acceptance restriction."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

class NativeToolsTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name('landmarksignal_native_policy.py')
        spec = importlib.util.spec_from_file_location('native_policy_test', path)
        self.policy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.policy)

    def test_native_worker_can_read_work_and_report_lifecycle(self):
        with patch.dict(sys.modules, {'landmarksignal_v1_scope': None}):
            for name in ('kanban_show', 'kanban_list', 'kanban_block',
                         'kanban_request_review', 'kanban_complete', 'terminal',
                         'write_file', 'delegate_task'):
                with self.subTest(tool=name):
                    self.assertIsNone(self.policy.decide(tool_name=name, args={}))

    def test_old_foreground_scope_does_not_lock_native_project_work(self):
        with patch.dict(sys.modules, {'landmarksignal_v1_scope': types.SimpleNamespace(acceptance=False)}):
            self.assertIsNone(self.policy.decide(tool_name='kanban_show', args={}))
            self.assertIsNone(self.policy.decide(tool_name='terminal', args={}))

    def test_explicit_acceptance_scope_remains_tool_free(self):
        with patch.dict(sys.modules, {'landmarksignal_v1_scope': types.SimpleNamespace(acceptance=True)}):
            self.assertEqual(self.policy.decide(tool_name='write_file', args={})['action'], 'block')

if __name__ == '__main__':
    unittest.main(verbosity=2)
