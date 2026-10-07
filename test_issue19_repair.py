import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from repair_issue19_card import repair, ROOT_ID, TASK_KEY, ISSUE_URL


class Issue19RepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "board.db"
        self.backup = Path(self.temp.name) / "backup/board.db"
        with sqlite3.connect(self.path) as c:
            c.executescript("""
CREATE TABLE tasks(id TEXT PRIMARY KEY,title TEXT,body TEXT,assignee TEXT,status TEXT,idempotency_key TEXT,block_kind TEXT,claim_lock TEXT,worker_pid INTEGER,block_recurrences INTEGER);
CREATE TABLE task_runs(id INTEGER PRIMARY KEY,task_id TEXT,status TEXT);
CREATE TABLE task_events(id INTEGER PRIMARY KEY,task_id TEXT,kind TEXT,payload TEXT,created_at INTEGER);
CREATE TABLE task_links(parent_id TEXT,child_id TEXT);
""")
            c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)", (ROOT_ID,"rewritten","lost link","jeeves","todo",TASK_KEY,"needs_input",None,None,3))
            c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)", ("child","generated","body","jeeves","ready",None,None,None,None,0))
            c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)", ("original","original","preserve",None,"ready",None,None,None,None,0))
            c.execute("INSERT INTO task_events VALUES(1,?,?,?,1)", (ROOT_ID,"decomposed",json.dumps({"child_ids":["child"]})))
            c.execute("INSERT INTO task_links VALUES('child',?)", (ROOT_ID,))

    def test_repair_backs_up_parks_graph_and_preserves_original(self):
        self.assertEqual(repair(self.path,self.backup,"reviewed issue body"),["child"])
        with sqlite3.connect(self.path) as c, sqlite3.connect(self.backup) as b:
            root = c.execute("SELECT body,status,assignee,block_recurrences FROM tasks WHERE id=?",(ROOT_ID,)).fetchone()
            self.assertEqual(root,(ISSUE_URL + "\n\nreviewed issue body","blocked",None,3))
            self.assertEqual(c.execute("SELECT status,assignee FROM tasks WHERE id='child'").fetchone(),("blocked",None))
            self.assertEqual(c.execute("SELECT * FROM tasks WHERE id='original'").fetchone(),b.execute("SELECT * FROM tasks WHERE id='original'").fetchone())
            self.assertEqual(b.execute("SELECT status FROM tasks WHERE id=?",(ROOT_ID,)).fetchone(),("todo",))
            self.assertEqual(c.execute("SELECT COUNT(*) FROM task_links").fetchone()[0],0)
            self.assertEqual(c.execute("SELECT kind FROM task_events WHERE id=1").fetchone(),("decomposed",))

    def test_running_child_refuses_repair_without_changes(self):
        with sqlite3.connect(self.path) as c:
            c.execute("UPDATE tasks SET status='running' WHERE id='child'")
        with self.assertRaisesRegex(RuntimeError,"worker/claim"):
            repair(self.path,self.backup,"reviewed issue body")
        self.assertFalse(self.backup.exists())
        with sqlite3.connect(self.path) as c:
            self.assertEqual(c.execute("SELECT status FROM tasks WHERE id=?",(ROOT_ID,)).fetchone(),("todo",))
            self.assertEqual(c.execute("SELECT COUNT(*) FROM task_events").fetchone()[0],1)


if __name__ == "__main__":
    unittest.main()
