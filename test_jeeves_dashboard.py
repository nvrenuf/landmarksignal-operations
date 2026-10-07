"""Launch boundary checks without a model, board mutation, or native worker."""
import importlib.util
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

import yaml
from install_jeeves_dashboard import enable_plugin
import prepare_issue7_retry as retry


class ConfigurationTests(unittest.TestCase):
    def test_enable_preserves_settings_and_is_repeatable(self):
        samples = [
            b"# retain\r\nmodel:\r\n  default: original\r\nplugins:\r\n  enabled:\r\n    - existing\r\n  isolation: host\r\nkanban:\r\n  max_spawn: 1\r\n",
            b"model: {default: original}\nplugins: {enabled: [existing], disabled: []}\n",
            b"model: {default: original}\n",
            b"plugins:\n  isolation: host\nmodel: {default: original}\n",
        ]
        for before in samples:
            with self.subTest(before=before):
                after = enable_plugin(before)
                original = yaml.safe_load(before)
                expected = {**original, "plugins": {**original.get("plugins", {}), "enabled": [*original.get("plugins", {}).get("enabled", []), "landmarksignal-launch"]}}
                self.assertEqual(yaml.safe_load(after), expected)
                self.assertEqual(enable_plugin(after), after)
                if before.startswith(b"# retain"):
                    self.assertTrue(after.startswith(b"# retain\r\nmodel:\r\n  default: original\r\n"))
                    self.assertTrue(after.endswith(b"kanban:\r\n  max_spawn: 1\r\n"))

    def test_disabled_plugin_is_not_overridden(self):
        with self.assertRaises(RuntimeError):
            enable_plugin(b"plugins: {disabled: [landmarksignal-launch]}\n")


class RetryTests(unittest.TestCase):
    def test_only_reviewed_failed_run_can_be_prepared(self):
        body = "reviewed body"
        card = {"id": retry.TASK, "status": "blocked", "idempotency_key": "landmarksignal-issue7-status-mapping-v1",
                "assignee": None, "body": body}
        digest = hashlib.sha256(body.encode()).hexdigest()
        evidence = {"status": "INCOMPLETE", "kanban_task_id": retry.TASK, "kanban_run_id": 11,
                    "issue_url": retry.ISSUE, "task_body_sha256": digest}
        launch = {"state": "incomplete", "task_id": retry.TASK}
        with patch.object(retry, "BODY_SHA", digest):
            retry.validate_failure(card, evidence, launch)
            for changes in ({"worker_pid": 123}, {"status": "running"}, {"id": "another-task"}):
                with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                    retry.validate_failure({**card, **changes}, evidence, launch)
            with self.assertRaises(RuntimeError):
                retry.validate_failure(card, {**evidence, "kanban_run_id": 12}, launch)


class LaunchTests(unittest.TestCase):
    def setUp(self):
        class HTTPException(Exception):
            def __init__(self, status_code, detail):
                super().__init__(detail)
                self.status_code = status_code
        class Router:
            def get(self, path): return lambda fn: fn
            def post(self, path): return lambda fn: fn
        fake = ModuleType("fastapi")
        fake.HTTPException, fake.APIRouter, fake.Request = HTTPException, Router, object
        pydantic = ModuleType("pydantic")
        pydantic.BaseModel = object
        with patch.dict(sys.modules, {"fastapi": fake, "pydantic": pydantic}):
            path = Path(__file__).parent / "plugins/landmarksignal-launch/dashboard/plugin_api.py"
            spec = importlib.util.spec_from_file_location("dashboard_contract_test", path)
            self.api = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.api)
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.work = self.root / "work"
        self.work.mkdir()
        self.board = self.root / "board.db"
        with sqlite3.connect(self.board) as conn:
            conn.execute("CREATE TABLE tasks(id TEXT, idempotency_key TEXT, body TEXT, workspace_kind TEXT, workspace_path TEXT, status TEXT, assignee TEXT, worker_pid INTEGER, claim_lock TEXT)")
            conn.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)", (self.api.TASK, self.api.KEY, self.api.ISSUE,
                         "dir", str(self.work), "blocked", None, None, None))
        self.paths = patch.object(self.api, "paths", return_value=(self.root, self.work, self.board))
        self.paths.start()
        self.gate = patch.object(self.api, "require_jeeves")
        self.gate.start()
        self.request = SimpleNamespace(headers={"origin": "http://127.0.0.1:9119"}, base_url="http://127.0.0.1:9119/")

    def tearDown(self):
        self.gate.stop()
        self.paths.stop()
        self.temp.cleanup()

    def approval(self):
        _, _, digest = self.api.inspect_card()
        return SimpleNamespace(phrase="APPROVE ISSUE 7", card_sha256=digest)

    def test_wrong_profile_is_rejected(self):
        self.gate.stop()
        config = ModuleType("hermes_cli.config")
        config.get_hermes_home = lambda: self.root / "profiles/gloria"
        package = ModuleType("hermes_cli")
        request = SimpleNamespace(query_params={"profile": "jeeves"})
        with patch.dict(sys.modules, {"hermes_cli": package, "hermes_cli.config": config}):
            with self.assertRaises(Exception): self.api.require_jeeves(request)
            config.get_hermes_home = lambda: self.root / "profiles/jeeves"
            self.api.require_jeeves(request)
            request.query_params["profile"] = "gloria"
            with self.assertRaises(Exception): self.api.require_jeeves(request)
        self.gate.start()

    def test_changed_card_and_cross_origin_launch_cannot_spawn(self):
        approval = self.approval()
        with sqlite3.connect(self.board) as conn:
            conn.execute("UPDATE tasks SET body=body||' changed'")
        with patch.object(self.api.subprocess, "Popen") as spawn:
            with self.assertRaises(Exception): self.api.start(self.request, approval)
            self.request.headers["origin"] = "https://another-site.invalid"
            with self.assertRaises(Exception): self.api.start(self.request, self.approval())
            spawn.assert_not_called()
        self.assertFalse((self.work / "dashboard-launch.json").exists())

    def test_duplicate_launch_and_running_card_cannot_spawn(self):
        (self.work / "dashboard-launch.json").write_text(json.dumps({"state": "launching"}))
        with patch.object(self.api.subprocess, "Popen") as spawn:
            with self.assertRaises(Exception): self.api.start(self.request, self.approval())
            spawn.assert_not_called()
        (self.work / "dashboard-launch.json").unlink()
        with sqlite3.connect(self.board) as conn:
            conn.execute("UPDATE tasks SET status='running'")
        with patch.object(self.api.subprocess, "Popen") as spawn:
            with self.assertRaises(Exception): self.api.start(self.request, self.approval())
            spawn.assert_not_called()

    def test_worker_start_is_exact_and_launch_is_consumed_once(self):
        python = self.root / "hermes-agent/venv/Scripts/python.exe"
        python.parent.mkdir(parents=True)
        python.touch()
        runner = Path(self.api.__file__).parent / "runner/guarded_issue7_document.py"
        with patch.object(Path, "is_file", side_effect=lambda: True), patch.object(self.api.subprocess, "Popen") as spawn, \
                patch.object(self.api.subprocess, "CREATE_NO_WINDOW", 0, create=True):
            self.assertTrue(self.api.start(self.request, self.approval())["started"])
            command = spawn.call_args.args[0]
            self.assertEqual(command, [str(python), "-B", str(runner), "--dashboard-approved-issue7"])
            self.assertEqual(spawn.call_args.kwargs["env"]["HERMES_PROFILE"], "jeeves")
            with self.assertRaises(Exception): self.api.start(self.request, self.approval())
            self.assertEqual(spawn.call_count, 1)


if __name__ == "__main__":
    unittest.main()
