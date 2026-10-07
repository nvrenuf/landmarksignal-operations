"""Document-contract and native-card preparation boundaries; no model or Windows mutation."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from document_tasks import get_spec, digest, task_body, find_card
from prepare_document_handoff import prepare_card, verify_assets, normalized_hash
import test_jeeves_dashboard as baseline


class DocumentLaunchTests(baseline.LaunchTests):
    def setUp(self):
        super().setUp()
        self.spec = get_spec("issue6-roster")
        self.request.query_params = {"profile": "jeeves", "task": "issue6-roster"}
        with closing(sqlite3.connect(self.board)) as conn:
            conn.execute("DELETE FROM tasks")
            conn.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)", ("t_roster", self.spec["key"], task_body(self.spec),
                         "dir", str(self.work), "blocked", None, None, None))
            conn.commit()

    def approval(self):
        _, _, card_hash = self.api.inspect_card("issue6-roster")
        return SimpleNamespace(phrase="APPROVE ISSUE 6", card_sha256=card_hash, contract_sha256=digest(self.spec))

    def test_worker_start_is_exact_and_launch_is_consumed_once(self):
        python = self.root / "hermes-agent/venv/Scripts/python.exe"
        python.parent.mkdir(parents=True)
        python.touch()
        runner = Path(self.api.__file__).parent / "runner/guarded_document_task.py"
        with patch.object(Path, "is_file", return_value=True), patch.object(self.api.subprocess, "Popen") as spawn, \
                patch.object(self.api.subprocess, "CREATE_NO_WINDOW", 0, create=True):
            self.api.start(self.request, self.approval())
            self.assertEqual(spawn.call_args.args[0], [str(python), "-B", str(runner), "--dashboard-approved-document", "issue6-roster"])
            record = json.loads((self.work / "dashboard-launch.json").read_text())
            self.assertEqual(record["task_id"], "t_roster")
            self.assertEqual(record["contract_sha256"], digest(self.spec))
            with self.assertRaises(Exception): self.api.start(self.request, self.approval())
            self.assertEqual(spawn.call_count, 1)

    def test_unknown_contract_and_cross_task_approval_cannot_spawn(self):
        approval = self.approval()
        with patch.object(self.api.subprocess, "Popen") as spawn:
            for phrase, contract in [("APPROVE ISSUE 7", digest(self.spec)), ("APPROVE ISSUE 6", "wrong")]:
                with self.assertRaises(Exception):
                    self.api.start(self.request, SimpleNamespace(phrase=phrase, card_sha256=approval.card_sha256, contract_sha256=contract))
            self.request.query_params["task"] = "../../arbitrary"
            with self.assertRaises(Exception): self.api.start(self.request, approval)
            spawn.assert_not_called()
        self.assertFalse((self.work / "dashboard-launch.json").exists())


class PreparationTests(unittest.TestCase):
    def test_create_is_atomic_held_and_repeatable_and_preserves_completed_card(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory) / "work"
            spec = get_spec("issue6-roster")
            with closing(sqlite3.connect(":memory:")) as conn:
                conn.row_factory = sqlite3.Row
                conn.execute("CREATE TABLE tasks(id TEXT, idempotency_key TEXT, body TEXT, workspace_kind TEXT, workspace_path TEXT, status TEXT, assignee TEXT, worker_pid INTEGER, claim_lock TEXT, block_kind TEXT)")
                conn.execute("CREATE TABLE task_events(task_id TEXT, kind TEXT, payload TEXT, created_at INTEGER)")
                conn.execute("INSERT INTO tasks(id,status) VALUES('t_0b33c85e','done')")
                conn.commit()
                original = dict(conn.execute("SELECT * FROM tasks").fetchone())
                def create(conn, **kwargs):
                    self.assertEqual(kwargs["initial_status"], "blocked")
                    self.assertEqual(kwargs["project_id"], "")
                    conn.execute("INSERT INTO tasks(id,idempotency_key,body,workspace_kind,workspace_path,status) VALUES(?,?,?,?,?,?)",
                                 ("t_new", kwargs["idempotency_key"], kwargs["body"], kwargs["workspace_kind"], kwargs["workspace_path"], kwargs["initial_status"]))
                    return "t_new"
                kb = SimpleNamespace(create_task=create, _has_sticky_block=lambda c,t: c.execute("SELECT 1 FROM task_events WHERE task_id=? AND kind='blocked'", (t,)).fetchone() is not None)
                self.assertEqual(prepare_card(conn, kb, spec, work), "t_new")
                self.assertEqual(prepare_card(conn, kb, spec, work), "t_new")
                self.assertEqual(conn.execute("SELECT count(*) FROM tasks").fetchone()[0], 2)
                self.assertEqual(dict(conn.execute("SELECT * FROM tasks WHERE id='t_0b33c85e'").fetchone()), original)
                conn.execute("UPDATE tasks SET body='rewritten' WHERE id='t_new'")
                conn.commit()
                with self.assertRaises(RuntimeError): prepare_card(conn, kb, spec, work)

    def test_asset_upgrade_refuses_unknown_local_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            path = target / "asset.py"
            path.write_bytes(b"old\r\n")
            old = {"asset.py": normalized_hash(b"old\n")}
            verify_assets(target, {"asset.py": b"new\n"}, old)
            path.write_bytes(b"local edit\n")
            with self.assertRaises(RuntimeError): verify_assets(target, {"asset.py": b"new\n"}, old)
            self.assertEqual(path.read_bytes(), b"local edit\n")


if __name__ == "__main__":
    unittest.main()
