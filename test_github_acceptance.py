"""Isolated GitHub/Kanban fixtures: no live issue, project or worker mutations."""
from contextlib import closing
import json
from pathlib import Path
import os
import sqlite3
import sys
import tempfile
import unittest

if os.name == 'nt':
    sys.path.insert(0, str(Path(os.environ['LOCALAPPDATA']) / 'hermes/hermes-agent'))
    import hermes_bootstrap
sys.path.insert(0, str(Path(__file__).resolve().parent))

import github_acceptance as acceptance
import github_handoff_results as results
import github_queue_intake as intake
from test_github_projects import source


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / 'kanban/boards/landmarksignal/kanban.db'
        self.db.parent.mkdir(parents=True)
        self.source = source(3, 47)
        self.work = self.root / 'landmarksignal-v1/work/github-intake/original'
        self.work.mkdir(parents=True)
        (self.work / 'github-source.json').write_text(json.dumps(self.source))
        (self.work / 'output.md').write_text('Verified fixture evidence')
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.executescript('CREATE TABLE tasks(id TEXT PRIMARY KEY,title TEXT,status TEXT,workspace_path TEXT,idempotency_key TEXT,completion_contract TEXT);'
                               'CREATE TABLE task_runs(id INTEGER PRIMARY KEY,task_id TEXT,profile TEXT,outcome TEXT,summary TEXT);'
                               'CREATE TABLE task_events(id INTEGER PRIMARY KEY,task_id TEXT,kind TEXT,payload TEXT,created_at INTEGER);')
            conn.execute('INSERT INTO tasks VALUES (?,?,?,?,?,?)',
                         ('root47', 'Original root', 'review', str(self.work), intake.key(self.source), None))
            conn.execute('INSERT INTO task_runs VALUES (?,?,?,?,?)', (29, 'root47', 'jeeves', 'review', 'Worker evidence'))
        self.comment = []
        self.calls = []
        self.issue_state = 'open'
        self.project_status = 'Human Review'
        self.pr_merged = True
        self.auto_close_on_done = False
        self.fail_once = None
        self.bad_binding = None

    def tearDown(self):
        self.tmp.cleanup()

    def reader(self, args, payload=None):
        self.calls.append((args, payload))
        endpoint = args[1]
        targeted = (self.fail_once == 'comments' and endpoint.endswith('/comments')
                    or self.fail_once == 'status' and endpoint == 'graphql' and payload['query'].startswith('mutation')
                    or self.fail_once == 'close' and endpoint.endswith('/issues/47') and '--method' in args)
        if targeted:
            failure, self.fail_once = self.fail_once, None
            raise RuntimeError('Simulated ' + failure + ' failure')
        if endpoint == 'user':
            return 'nvrenuf'
        if endpoint == 'graphql':
            if payload['query'].startswith('mutation'):
                self.project_status = 'Done'
                if self.auto_close_on_done:
                    self.issue_state = 'closed'
                return json.dumps({'data':{'updateProjectV2ItemFieldValue':{'projectV2Item':{'id':self.source['project_item_id']}}}})
            project = {'id':self.source['project_id'], 'number':3, 'closed':False,
                       'owner':{'login':'nvrenuf'}, 'fields':{'pageInfo':{'hasNextPage':False},
                       'nodes':[{'id':'F_STATUS','name':'Status','options':[{'id':'O_DONE','name':'Done'}]}]}}
            item = {'id':self.source['project_item_id'], 'isArchived':False,
                    'project':{'id':self.source['project_id']},'content':{
                        'id':self.source['issue']['id'],'url':self.source['issue']['url'],
                        'number':47,'repository':{'nameWithOwner':'nvrenuf/repo'}},
                    'fieldValueByName':{'name':self.project_status}}
            if self.bad_binding == 'item':item['id'] = 'other'
            if self.bad_binding == 'repository':item['content']['repository']['nameWithOwner'] = 'other/repo'
            return json.dumps({'data':{'project':project,'item':item}})
        if endpoint == 'repos/nvrenuf/repo/pulls/99':
            return json.dumps({'number':99,'html_url':'https://github.com/nvrenuf/repo/pull/99',
                               'merged':self.pr_merged,'merged_at':'2026-10-08T00:00:00Z' if self.pr_merged else None,
                               'base':{'repo':{'full_name':'nvrenuf/repo'}}})
        issue = 'repos/nvrenuf/repo/issues/47'
        if endpoint == issue + '/comments':
            if '--method' in args:
                self.comment.append(payload)
                if self.fail_once == 'comments_post_after':
                    self.fail_once = None
                    raise RuntimeError('Simulated lost POST response')
                return '{}'
            return json.dumps([self.comment])
        if endpoint == issue:
            if '--method' in args:
                self.issue_state = 'closed'
                return '{}'
            return json.dumps({'state':self.issue_state,'node_id':self.source['issue']['id'],
                               'html_url':self.source['issue']['url'],'number':47})
        raise AssertionError(endpoint)

    def native_complete(self, conn, task_id, **kwargs):
        self.assertEqual(task_id, 'root47')
        self.assertTrue(kwargs['force'])
        self.assertTrue(kwargs['metadata']['human_acceptance']['marker'])
        conn.execute("UPDATE tasks SET status='done' WHERE id=?", (task_id,))
        conn.commit()
        return True

    def snapshot(self):
        return results.inspect_results(self.root, 'nvrenuf/3')[0]['snapshot_sha256']

    def accept(self, *, requirement='required', pr_url='https://github.com/nvrenuf/repo/pull/99',
               selector='nvrenuf/3', snapshot=None):
        return acceptance.accept_complete(self.root, 'root47', snapshot or self.snapshot(),
            'Lee reviewed the implementation and tests', requirement, pr_url,
            'ACCEPT root47', self.reader, selector, self.native_complete)

    def test_explicit_acceptance_order_and_duplicate_retry(self):
        first = self.accept()
        self.assertTrue(first['acceptance_verified'])
        self.assertEqual(self.issue_state, 'closed')
        self.assertEqual(self.project_status, 'Done')
        self.assertEqual(len(self.comment), 1)
        post = next(i for i,(a,_) in enumerate(self.calls) if a[1].endswith('/comments') and '--method' in a)
        done = next(i for i,(a,p) in enumerate(self.calls) if a[1]=='graphql' and p['query'].startswith('mutation'))
        close = next(i for i,(a,_) in enumerate(self.calls) if a[1].endswith('/issues/47') and '--method' in a)
        self.assertLess(post, done)
        self.assertLess(done, close)
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM task_events WHERE kind='human_accepted'").fetchone()[0],1)
            self.assertEqual(conn.execute("SELECT status FROM tasks WHERE id='root47'").fetchone()[0],'done')
        self.accept()
        self.assertEqual(len(self.comment),1)
        self.assertEqual(sum(1 for a,_ in self.calls if a[1].endswith('/issues/47') and '--method' in a),1)

    def test_required_merge_and_identity_checks_before_acceptance(self):
        self.pr_merged = False
        with self.assertRaisesRegex(RuntimeError, 'not verified merged'):
            self.accept()
        self.pr_merged = True
        for bad in ('item','repository'):
            self.bad_binding = bad
            with self.assertRaisesRegex(RuntimeError, 'binding differs'):
                self.accept()
        self.bad_binding = None
        with self.assertRaises(RuntimeError):
            self.accept(selector='nvrenuf/4')
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM task_events').fetchone()[0],0)
            self.assertEqual(conn.execute("SELECT status FROM tasks WHERE id='root47'").fetchone()[0],'review')

    def test_native_pr_contract_refuses_no_merge_attestation(self):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("UPDATE tasks SET completion_contract='nvrenuf/repo' WHERE id='root47'")
        with self.assertRaisesRegex(RuntimeError,'native task requires a merged PR'):
            self.accept(requirement='not_required',pr_url='')
        self.assertEqual(self.comment,[])

    def _partial_then_retry(self, step):
        self.fail_once = step
        with self.assertRaisesRegex(RuntimeError, 'Retry Sync completion'):
            self.accept()
        self.accept()
        self.assertEqual(len(self.comment),1)
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM task_events WHERE kind='human_accepted'").fetchone()[0],1)

    def test_comment_failure_retry(self):
        self._partial_then_retry('comments')

    def test_project_status_failure_retry(self):
        self._partial_then_retry('status')

    def test_issue_closure_failure_retry(self):
        self._partial_then_retry('close')

    def test_lost_comment_response_does_not_duplicate_evidence(self):
        self._partial_then_retry('comments_post_after')

    def test_done_workflow_closes_issue_without_second_close(self):
        self.auto_close_on_done = True
        self.accept(requirement='not_required', pr_url='')
        self.assertEqual(self.issue_state,'closed')
        self.assertEqual(len(self.comment),1)
        self.assertFalse(any(a[1].endswith('/issues/47') and '--method' in a for a,_ in self.calls))

    def test_subtask_and_historical_done_do_not_imply_acceptance(self):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("INSERT INTO tasks VALUES ('child','Child','review',?,?,null)",
                         (str(self.work), 'decomposed-child'))
            conn.execute("INSERT INTO task_runs VALUES (30,'child','jeeves','review','Child evidence')")
        with self.assertRaisesRegex(RuntimeError, 'changed'):
            acceptance.accept_complete(self.root, 'child', 'anything', 'accept', 'not_required', '',
                                       'ACCEPT child', self.reader, 'nvrenuf/3', self.native_complete)
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("UPDATE tasks SET status='done' WHERE id='root47'")
        with self.assertRaisesRegex(RuntimeError, 'Only an original intake root in Review'):
            self.accept(requirement='not_required', pr_url='')
        self.assertEqual(self.comment, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
