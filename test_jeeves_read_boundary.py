"""Card reads and owned blocker reporting do not grant execution permission."""
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from landmarksignal_policy import decide


class ReadBoundaryTests(unittest.TestCase):
    def test_replacement_is_atomic_and_permission_failure_does_not_retry(self):
        from repair_jeeves_read_boundary import replace
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.py"
            path.write_bytes(b"old")
            with patch("pathlib.Path.open", side_effect=PermissionError("protected")) as opened:
                with self.assertRaises(PermissionError):
                    replace(path, b"new")
                self.assertEqual(opened.call_count, 1)
            self.assertEqual(path.read_bytes(), b"old")
            replace(path, b"new")
            self.assertEqual(path.read_bytes(), b"new")
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_card_reads_allowed_while_execution_remains_denied(self):
        for name in ("kanban_show", "kanban_list", "kanban_attachments"):
            self.assertIsNone(decide(name, {"board": "landmarksignal"}))
        for name in ("write_file", "terminal", "execute_code", "delegate_task", "kanban_create",
                     "kanban_complete", "kanban_request_review", "kanban_unblock", "kanban_block"):
            self.assertEqual(decide(name, {})["action"], "block")

    def test_native_block_requires_exact_live_claim_and_cannot_change_other_cards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "hermes"
            database = root / "kanban/boards/landmarksignal/kanban.db"
            database.parent.mkdir(parents=True)
            connection = sqlite3.connect(database)
            try:
                connection.executescript(
                    "CREATE TABLE tasks(id,status,assignee,current_run_id,claim_lock,worker_pid);"
                    "CREATE TABLE task_runs(id,task_id,status,profile,claim_lock);"
                )
                connection.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?)",
                                   ("t_test", "running", "jeeves", 7, "claim", os.getpid()))
                connection.execute("INSERT INTO task_runs VALUES(?,?,?,?,?)",
                                   (7, "t_test", "running", "jeeves", "claim"))
                connection.commit()
                environment = {
                    "LOCALAPPDATA": directory, "HERMES_PROFILE": "jeeves",
                    "HERMES_HOME": str(root / "profiles/jeeves"),
                    "HERMES_KANBAN_DB": str(database), "HERMES_KANBAN_TASK": "t_test",
                    "HERMES_KANBAN_RUN_ID": "7", "HERMES_KANBAN_CLAIM_LOCK": "claim",
                }
                args = {"task_id": "t_test", "board": "landmarksignal",
                        "kind": "needs_input", "reason": "Execution approval needed"}
                with patch.dict(os.environ, environment):
                    before = connection.execute("SELECT * FROM tasks").fetchall()
                    self.assertIsNone(decide("kanban_block", args))
                    self.assertEqual(connection.execute("SELECT * FROM tasks").fetchall(), before)
                    for change in ({"task_id": "t_other"}, {"kind": "transient"},
                                   {"board": "other"}, {"reason": ""}):
                        self.assertEqual(decide("kanban_block", {**args, **change})["action"], "block")
                    for name, value in (("HERMES_KANBAN_RUN_ID", "8"),
                                        ("HERMES_KANBAN_CLAIM_LOCK", "wrong"),
                                        ("HERMES_PROFILE", "default"),
                                        ("HERMES_HOME", str(root)),
                                        ("HERMES_KANBAN_DB", str(root / "other.db"))):
                        with patch.dict(os.environ, {name: value}):
                            self.assertEqual(decide("kanban_block", args)["action"], "block")
                    for field, value in (("worker_pid", os.getpid() + 1), ("status", "blocked"),
                                         ("assignee", "default")):
                        connection.execute(f"UPDATE tasks SET {field}=?", (value,))
                        connection.commit()
                        self.assertEqual(decide("kanban_block", args)["action"], "block")
                        connection.execute("UPDATE tasks SET worker_pid=?,status='running',assignee='jeeves'",
                                           (os.getpid(),))
                        connection.commit()
                    connection.execute("UPDATE task_runs SET status='crashed'")
                    connection.commit()
                    self.assertEqual(decide("kanban_block", args)["action"], "block")
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
