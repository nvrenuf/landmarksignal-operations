from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import github_queue_intake as intake
import install_github_intake as installer


def record(n=1):
    body = 'Original requirements: do one bounded task. Depends on #3.'
    return {'project_id':'P_3','project_item_id':'PI_'+str(n),'project_number':3,'project_owner':'nvrenuf',
            'source_status':'Queued for Jeeves','source_body_sha256':hashlib.sha256(body.encode()).hexdigest(),
            'github_blockers':[{'url':'https://github.com/nvrenuf/repo/issues/3','title':'Prerequisite','state':'open'}],
            'issue':{'__typename':'Issue','id':'I_'+str(n),'number':n,'title':'Task '+str(n),
                     'url':'https://github.com/nvrenuf/repo/issues/'+str(n),
                     'body':body,'updatedAt':'2026-10-07T00:00:00Z','state':'OPEN',
                     'repository':{'nameWithOwner':'nvrenuf/repo'}}}


class ReadTests(unittest.TestCase):
    def test_wrong_account_refuses_before_project_read(self):
        calls=[]
        def reader(args, payload=None): calls.append(args); return 'another-account'
        with self.assertRaises(RuntimeError): intake.read_queue(reader)
        self.assertEqual(len(calls),1)

    def test_paginated_selection_filters_status_archive_type_and_preserves_blockers(self):
        records=[record(1),record(2)]
        calls=[]
        def reader(args,payload=None):
            calls.append((args,payload))
            if args[1]=='user': return 'nvrenuf\n'
            if args[1]!='graphql': return json.dumps([[{'html_url':'https://github.com/nvrenuf/repo/issues/3','title':'Prerequisite','state':'open'}]])
            n=1 if payload['variables']['cursor'] is None else 2
            item={'id':'PI_'+str(n),'isArchived':False,'content':records[n-1]['issue'],
                  'fieldValues':{'pageInfo':{'hasNextPage':False},'nodes':[{'name':'Queued for Jeeves','field':{'name':'Status'}}]}}
            nodes=[item, {**item,'id':'archived','isArchived':True}, {**item,'id':'draft','content':{'__typename':'DraftIssue'}},
                   {**item,'id':'otherstatus','fieldValues':{'pageInfo':{'hasNextPage':False},'nodes':[{'name':'Defined','field':{'name':'Status'}}]}}]
            return json.dumps({'data':{'user':{'projectV2':{'id':'P_3','title':'Project','items':{
                'nodes':nodes,'pageInfo':{'hasNextPage':n==1,'endCursor':'cursor1'}}}}}})
        actual=intake.read_queue(reader)
        self.assertEqual([r['issue']['number'] for r in actual],[1,2])
        self.assertEqual(actual[0]['github_blockers'],records[0]['github_blockers'])
        self.assertTrue(all(a[0][0]=='api' for a in calls))


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.conn=sqlite3.connect(':memory:')
        self.conn.row_factory=sqlite3.Row
        self.conn.execute('CREATE TABLE tasks(id TEXT PRIMARY KEY,idempotency_key TEXT,body TEXT,status TEXT,assignee TEXT,claim_lock TEXT,worker_pid INTEGER,title TEXT,workspace_path TEXT)')
        self.conn.execute("INSERT INTO tasks VALUES ('original',null,'Existing', 'done',null,null,null,'Preserve',null)")
        self.conn.commit()
        self.count=0
        def create(conn,**kwargs):
            self.count+=1
            task='t_'+str(self.count)
            conn.execute('INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?)',(task,kwargs['idempotency_key'],kwargs['body'],
                'triage' if kwargs['triage'] else 'ready',kwargs['assignee'],None,None,kwargs['title'],kwargs['workspace_path']))
            return task
        self.kb=SimpleNamespace(create_task=create)
    def tearDown(self):
        self.conn.close();self.temp.cleanup()
    def test_batch_repeated_import_preserves_cards_and_source_and_never_assigns(self):
        before=dict(self.conn.execute('SELECT * FROM tasks').fetchone())
        first=intake.import_records(self.conn,self.kb,[record(1),record(2)],self.root)
        again=intake.import_records(self.conn,self.kb,[record(1),record(2)],self.root)
        self.assertEqual(len(first['created']),2)
        self.assertEqual(len(again['existing']),2)
        self.assertEqual(again['created'],[])
        self.assertEqual(before,dict(self.conn.execute("SELECT * FROM tasks WHERE id='original'").fetchone()))
        self.assertEqual(self.conn.execute('SELECT count(*) FROM tasks').fetchone()[0],3)
        for row in self.conn.execute("SELECT * FROM tasks WHERE id!='original'"):
            self.assertEqual(row['status'],'triage');self.assertIsNone(row['assignee'])
            source=json.loads((Path(row['workspace_path'])/'github-source.json').read_text())
            self.assertIn(source['issue']['body'],row['body'])
            self.assertIn(source['github_blockers'][0]['url'],row['body'])
    def test_creation_failure_rolls_back_whole_batch(self):
        real=self.kb.create_task
        def failing(conn,**kwargs):
            if self.count: raise RuntimeError('Simulated native failure')
            return real(conn,**kwargs)
        self.kb.create_task=failing
        with self.assertRaises(RuntimeError):intake.import_records(self.conn,self.kb,[record(1),record(2)],self.root)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM tasks').fetchone()[0],1)
    def test_existing_linked_card_is_preserved_instead_of_duplicated(self):
        self.conn.execute("UPDATE tasks SET body=? WHERE id='original'",(record()['issue']['url'],));self.conn.commit()
        result=intake.import_records(self.conn,self.kb,[record()],self.root)
        self.assertEqual(result['created'],[]);self.assertEqual(result['existing'][0]['task_id'],'original')
    def test_dependency_reference_and_issue_number_prefix_are_not_existing_source_links(self):
        self.conn.execute("UPDATE tasks SET body=? WHERE id='original'", ('Source: https://github.com/nvrenuf/repo/issues/19\nDepends on https://github.com/nvrenuf/repo/issues/1',));self.conn.commit()
        result=intake.import_records(self.conn,self.kb,[record(1)],self.root)
        self.assertEqual(len(result['created']),1)

    def test_running_task_refuses_without_new_snapshot(self):
        self.conn.execute("UPDATE tasks SET status='running'");self.conn.commit()
        with self.assertRaises(RuntimeError):intake.import_records(self.conn,self.kb,[record()],self.root)
        self.assertFalse(list(self.root.iterdir()))


class InstallTests(unittest.TestCase):
    def test_crlf_payload_backup_idempotence_unknown_edit_and_rollback(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source';target=root/'target';recovery=root/'backup'
            mapping={'dashboard/plugin_api.py':'plugins/landmarksignal-launch/dashboard/plugin_api.py',
                'dashboard/dist/index.js':'plugins/landmarksignal-launch/dashboard/dist/index.js',
                'dashboard/runner/github_queue_intake.py':'github_queue_intake.py'}
            old={};new={}
            for name,src in mapping.items():
                path=source/src;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'new\r\n')
                new[name]=installer.sha(b'new\n')
                if 'runner' not in name:
                    out=target/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b'old\r\n');old[name]=installer.sha(b'old\n')
            (source/'github_intake_assets.json').write_text(json.dumps({'old_sha256':old,'new_sha256':new}))
            replace=installer.os.replace; calls=[]
            def fail_second(a,b):
                calls.append(str(b))
                if len(calls)==2:raise PermissionError('Simulated locked file')
                return replace(a,b)
            with patch.object(installer.os,'replace',fail_second),self.assertRaises(PermissionError):installer.install(source,target,recovery)
            self.assertEqual((target/'dashboard/plugin_api.py').read_bytes(),b'old\r\n')
            backup=installer.install(source,target,recovery)
            self.assertEqual((backup/'plugin-before/dashboard/plugin_api.py').read_bytes(),b'old\r\n')
            self.assertIsNone(installer.install(source,target,recovery))
            (target/'dashboard/plugin_api.py').write_text('unknown edit')
            with self.assertRaises(RuntimeError):installer.install(source,target,recovery)
            self.assertEqual((target/'dashboard/plugin_api.py').read_text(),'unknown edit')


import test_jeeves_dashboard as dashboard_tests

class IntakeBoundaryTests(dashboard_tests.LaunchTests):
    def test_batch_import_rejects_cross_origin_before_read(self):
        with patch.object(intake, 'run_intake') as run:
            self.request.headers['origin']='https://other.invalid'
            with self.assertRaises(Exception): self.api.github_intake(self.request)
            run.assert_not_called()

    def test_batch_import_calls_only_pinned_root_and_no_worker_spawn(self):
        with patch.object(intake, 'run_intake', return_value={'created': []}) as run, patch.object(self.api.subprocess, 'Popen') as spawn:
            self.assertEqual(self.api.github_intake(self.request), {'created': []})
            run.assert_called_once_with(self.root)
            spawn.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
