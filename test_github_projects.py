"""Isolated fixtures only: never import cards or post evidence to live services."""
import copy
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

if os.name == 'nt':
    sys.path.insert(0, str(Path(os.environ['LOCALAPPDATA'])/'hermes/hermes-agent'))
    import hermes_bootstrap
sys.path.insert(0, str(Path(__file__).resolve().parent))

import github_projects as projects
import github_queue_intake as intake
import github_handoff_results as returns
from test_github_intake import record
import test_github_intake as intake_tests
import test_jeeves_dashboard as dashboard_tests


def source(number=3, issue=1):
    r=record(issue)
    r.update(project_number=number, project_id=projects.get_project(f'nvrenuf/{number}')['id'],
             project_item_id=f'PI{number}_{issue}',
             project_fields={'Priority':'P1','Execution Order':7,'Sprint':'Sprint 001'})
    return r


class SelectionTests(unittest.TestCase):
    def test_discovery_paginates_open_owner_projects_and_reports_missing_status(self):
        previous=projects._discovered.copy();loaded=projects._catalog_loaded
        cursors=[]
        def fixture(number, *, closed=False, options=projects.REQUIRED_STATUS):
            return {'id':projects.PROJECTS.get(f'nvrenuf/{number}',{}).get('id',f'PVT_{number}'),
                    'number':number,'title':f'Project {number}','closed':closed,
                    'owner':{'login':'nvrenuf'},'fields':{'pageInfo':{'hasNextPage':False},
                    'nodes':[{'name':'Status','options':[{'name':name} for name in options]}]}}
        def reader(args,payload=None):
            if args[1]=='user':return 'nvrenuf'
            cursor=payload['variables']['cursor'];cursors.append(cursor)
            nodes=[fixture(3),fixture(6,closed=True)] if cursor is None else [fixture(4),fixture(5,options=('Done',))]
            return json.dumps({'data':{'user':{'login':'nvrenuf','projectsV2':{
                'nodes':nodes,'pageInfo':{'hasNextPage':cursor is None,'endCursor':'next'}}}}})
        try:
            discovered=projects.discover_projects(reader)
            self.assertEqual(cursors,[None,'next'])
            self.assertEqual({p['selector'] for p in discovered},{'nvrenuf/3','nvrenuf/4','nvrenuf/5'})
            self.assertFalse(projects.get_project('nvrenuf/5')['status_ready'])
            self.assertEqual(projects.get_project('nvrenuf/5')['missing_status'],
                             ['Queued for Jeeves','Human Review','Blocked'])
            with self.assertRaisesRegex(RuntimeError,'Status options'):
                projects.require_import_status(projects.get_project('nvrenuf/5'))
        finally:
            projects._discovered.clear();projects._discovered.update(previous)
            projects._catalog_loaded=loaded

    def test_successful_catalog_excludes_static_projects_even_when_empty(self):
        previous=projects._discovered.copy();loaded=projects._catalog_loaded
        def reader(args,payload=None):
            if args[1]=='user': return 'nvrenuf'
            return json.dumps({'data':{'user':{'login':'nvrenuf','projectsV2':{
                'nodes':self.nodes,'pageInfo':{'hasNextPage':False,'endCursor':None}}}}})
        try:
            self.nodes=[{'id':'PVT_5','number':5,'title':'Only open project','closed':False,
                         'owner':{'login':'nvrenuf'},'fields':{'pageInfo':{'hasNextPage':False},'nodes':[]}}]
            self.assertEqual([p['selector'] for p in projects.discover_projects(reader)],['nvrenuf/5'])
            self.assertEqual(projects.get_project('nvrenuf/5')['id'],'PVT_5')
            for selector in ('nvrenuf/3','nvrenuf/4'):
                with self.subTest(selector=selector),self.assertRaisesRegex(RuntimeError,'discovered catalog'):
                    projects.get_project(selector)
            self.nodes=[]
            self.assertEqual(projects.discover_projects(reader),[])
            for selector in ('nvrenuf/3','nvrenuf/4','nvrenuf/5'):
                with self.subTest(empty=selector),self.assertRaisesRegex(RuntimeError,'discovered catalog'):
                    projects.get_project(selector)
        finally:
            projects._discovered.clear();projects._discovered.update(previous)
            projects._catalog_loaded=loaded

    def test_discovery_failure_retains_last_good_catalog(self):
        previous=projects._discovered.copy();loaded=projects._catalog_loaded
        try:
            projects._discovered.clear()
            projects._discovered['nvrenuf/5']={'owner':'nvrenuf','number':5,'id':'OLD','title':'Old'}
            projects._catalog_loaded=True
            def stuck(args,payload=None):
                if args[1]=='user':return 'nvrenuf'
                return json.dumps({'data':{'user':{'login':'nvrenuf','projectsV2':{
                    'nodes':[],'pageInfo':{'hasNextPage':True,'endCursor':'same'}}}}})
            with self.assertRaisesRegex(RuntimeError,'pagination'):
                projects.discover_projects(stuck)
            self.assertEqual(projects.get_project('nvrenuf/5')['id'],'OLD')
            with self.assertRaisesRegex(RuntimeError,'discovered catalog'):
                projects.get_project('nvrenuf/3')
            with self.assertRaisesRegex(RuntimeError,'authenticate as nvrenuf'):
                projects.discover_projects(lambda *_:'wrong')
        finally:
            projects._discovered.clear();projects._discovered.update(previous)
            projects._catalog_loaded=loaded

    def test_unknown_source_refuses_before_read(self):
        for selector in ('nvrenuf/5','other/3','',None,3):
            with self.subTest(selector=selector), self.assertRaises(RuntimeError):
                intake.read_queue(lambda *args: self.fail('Unexpected GitHub call'), selector)

    def test_explicit_destinations_and_unmapped_projects_fail_closed(self):
        self.assertEqual(projects.get_destination('nvrenuf/3'),
                         {'board':'landmarksignal','assignee':None,'selector':'nvrenuf/3',
                          'project_id':projects.PROJECTS['nvrenuf/3']['id']})
        self.assertEqual(projects.get_destination('nvrenuf/9'),
                         {'board':'model-factory','assignee':'model-factory','selector':'nvrenuf/9',
                          'project_id':projects.PROJECTS['nvrenuf/9']['id']})
        previous=projects._discovered.copy();loaded=projects._catalog_loaded
        try:
            projects._discovered['nvrenuf/5']={'owner':'nvrenuf','number':5,'id':'PVT_5',
                'title':'New source','status_ready':True,'missing_status':[]}
            with self.assertRaisesRegex(RuntimeError,'no configured Hermes destination'):
                projects.get_destination('nvrenuf/5')
            with self.assertRaisesRegex(RuntimeError,'no configured Hermes destination'):
                intake.read_queue(lambda *args:self.fail('Unexpected GitHub call'),'nvrenuf/5')
        finally:
            projects._discovered.clear();projects._discovered.update(previous)
            projects._catalog_loaded=loaded

    def test_missing_status_field_refuses_before_dependencies_or_import(self):
        calls=[]
        def reader(args,payload=None):
            calls.append(args)
            if args[1]=='user':return 'nvrenuf'
            self.assertEqual(args[1],'graphql')
            return json.dumps({'data':{'user':{'projectV2':{
                'id':projects.PROJECTS['nvrenuf/3']['id'],'number':3,'owner':{'login':'nvrenuf'},
                'fields':{'pageInfo':{'hasNextPage':False},'nodes':[{'name':'Status','options':[{'name':'Done'}]}]},
                'items':{'pageInfo':{'hasNextPage':False},'nodes':[]}}}}})
        with self.assertRaisesRegex(RuntimeError,'missing required existing Status configuration'):
            intake.read_queue(reader,'nvrenuf/3')
        self.assertEqual([a[1] for a in calls],['user','graphql'])

    def test_queue_isolation_identity_and_closed_filter(self):
        for n in (3,4,9):
            calls=[]
            def reader(args,payload=None):
                calls.append((args,payload))
                if args[1]=='user': return 'nvrenuf'
                if args[1]!='graphql': return json.dumps([[{'html_url':'https://github.com/nvrenuf/repo/issues/3','state':'open','title':'Dependency'}]])
                self.assertEqual(payload['variables']['number'],n)
                item={'id':source(n)['project_item_id'],'isArchived':False,'content':source(n)['issue'],
                      'fieldValues':{'pageInfo':{'hasNextPage':False},'nodes':[
                          {'name':'Queued for Jeeves','field':{'name':'Status'}},
                          {'name':'P1','field':{'name':'Priority'}},
                          {'number':7,'field':{'name':'Execution Order'}},
                          {'title':'Sprint 001','field':{'name':'Sprint'}}]}}
                return json.dumps({'data':{'user':{'projectV2':{
                    'id':projects.get_project(f'nvrenuf/{n}')['id'],'number':n,'owner':{'login':'nvrenuf'},
                    'fields':{'pageInfo':{'hasNextPage':False},'nodes':[{'name':'Status','options':[
                        {'name':name} for name in projects.REQUIRED_STATUS]}]},
                    'items':{'pageInfo':{'hasNextPage':False},'nodes':[item,
                        {**item,'content':{**item['content'],'state':'CLOSED'}}]}}}}})
            result=intake.read_queue(reader,f'nvrenuf/{n}')
            self.assertEqual(len(result),1)
            self.assertEqual(result[0]['project_number'],n)
            self.assertEqual(result[0]['project_fields'],source(n)['project_fields'])
            self.assertEqual(result[0]['github_blockers'][0]['title'],'Dependency')
            def wrong(args,payload=None):
                text=reader(args,payload)
                return text.replace(projects.get_project(f'nvrenuf/{n}')['id'],'UNAPPROVED')
            with self.assertRaisesRegex(RuntimeError,'identity'): intake.read_queue(wrong,f'nvrenuf/{n}')


class ProjectImportTests(intake_tests.ImportTests):
    def test_model_factory_import_routes_board_and_assignee(self):
        new=source(9)
        created=intake.import_records(self.conn,self.kb,[new],self.root,'nvrenuf/9')
        self.assertEqual(len(created['created']),1)
        task=created['created'][0]['task_id']
        row=self.conn.execute('SELECT * FROM tasks WHERE id=?',(task,)).fetchone()
        self.assertEqual(row['status'],'triage')
        self.assertEqual(row['assignee'],'model-factory')
        self.assertEqual(projects.get_destination('nvrenuf/9')['board'],'model-factory')
        self.assertEqual(row['idempotency_key'],'github-project:'+new['project_id']+':'+new['issue']['id'])

    def test_discovered_project_without_destination_refuses_import(self):
        previous=projects._discovered.copy();loaded=projects._catalog_loaded
        # Build the record before narrowing the catalog to #5: record() resolves the
        # default nvrenuf/3 project id, which would no longer be in the narrowed catalog.
        new=record(5)
        new.update(project_number=5,project_id='PVT_5',project_item_id='PI5_5',
                   project_fields={'Priority':'P1','Execution Order':7,'Sprint':'Sprint 001'})
        try:
            projects._discovered['nvrenuf/5']={'owner':'nvrenuf','number':5,'id':'PVT_5',
                'title':'New source','status_ready':True,'missing_status':[]}
            projects._catalog_loaded=True
            with self.assertRaisesRegex(RuntimeError,'no configured Hermes destination'):
                intake.import_records(self.conn,self.kb,[new],self.root,'nvrenuf/5')
        finally:
            projects._discovered.clear();projects._discovered.update(previous)
            projects._catalog_loaded=loaded

    def test_same_issue_two_projects_duplicate_batch_and_archived_records(self):
        a=source(3); b=source(4)
        first=intake.import_records(self.conn,self.kb,[a,a],self.root)
        self.assertEqual(len(first['created']),1)
        self.assertEqual(len(first['existing']),1)
        second=intake.import_records(self.conn,self.kb,[b],self.root,'nvrenuf/4')
        self.assertEqual(len(second['created']),1)
        self.conn.execute('ALTER TABLE tasks ADD COLUMN archived_at TEXT')
        self.conn.execute("UPDATE tasks SET archived_at='2026-10-08',status='done'")
        self.conn.commit()
        before=[dict(r) for r in self.conn.execute('SELECT * FROM tasks')]
        for selector,r in (('nvrenuf/3',a),('nvrenuf/4',b)):
            result=intake.import_records(self.conn,self.kb,[r],self.root,selector)
            self.assertEqual(len(result['existing']),1);self.assertFalse(result['created'])
        self.assertEqual(before,[dict(r) for r in self.conn.execute('SELECT * FROM tasks')])
        self.assertEqual(intake.key(a),'github-project3:'+a['project_id']+':'+a['issue']['id'])
        self.assertNotEqual(intake.key(a),intake.key(b))

    def test_mixed_or_invalid_batch_refuses_without_any_changes(self):
        for records in ([source(3),source(4)],[{**source(3),'project_id':'wrong'}],
                        [{**source(3),'source_body_sha256':'changed'}]):
            with self.assertRaises(RuntimeError):intake.import_records(self.conn,self.kb,records,self.root)
            self.assertEqual(self.conn.execute('SELECT count(*) FROM tasks').fetchone()[0],1)
            self.assertFalse(list(self.root.iterdir()))


class ResultTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.db=self.root/'kanban/boards/landmarksignal/kanban.db';self.db.parent.mkdir(parents=True)
        self.sources={};self.comments=[];self.calls=[];self.bad=None
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.executescript('CREATE TABLE tasks(id,title,status,workspace_path,idempotency_key,archived_at); CREATE TABLE task_runs(id,task_id,profile,outcome,summary);')
            for n in (3,4):
                r=source(n);self.sources[n]=r
                work=self.root/f'landmarksignal-v1/work/github-intake/{n}';work.mkdir(parents=True)
                (work/'github-source.json').write_text(json.dumps(r))
                (work/'output.md').write_text('Isolated fixture artifact')
                conn.execute('INSERT INTO tasks VALUES (?,?,?,?,?,?)',(f't{n}','Fixture','review',str(work),intake.key(r),None))
                conn.execute('INSERT INTO task_runs VALUES (?,?,?,?,?)',(n,f't{n}','jeeves','review','Isolated summary'))

    def tearDown(self): self.temp.cleanup()

    def reader(self,args,payload=None):
        self.calls.append((args,payload))
        r=self.sources[self.number]
        if args[1]=='user':return 'nvrenuf'
        if args[1]=='graphql':
            q=payload['query']
            if q.startswith('mutation'):
                self.assertEqual(payload['variables'],{'project':r['project_id'],'item':r['project_item_id'],'field':'STATUS','option':self.status})
                return json.dumps({'data':{}})
            if 'fieldValueByName' in q:return json.dumps({'data':{'node':{'fieldValueByName':{'name':self.status}}}})
            data={'project':{'id':r['project_id'],'number':self.number,'closed':self.bad=='closed','owner':{'login':'nvrenuf'},
                'fields':{'pageInfo':{'hasNextPage':False},'nodes':[{'id':'STATUS','name':'Status','options':[{'id':self.status,'name':self.status}]}]}},
                'item':{'id':r['project_item_id'],'isArchived':False,'project':{'id':r['project_id']},'content':copy.deepcopy(r['issue'])}}
            if self.bad=='item':data['item']['id']='wrong'
            if self.bad=='project':data['item']['project']['id']='wrong'
            if self.bad=='issue':data['item']['content']['id']='wrong'
            if self.bad=='repo':data['item']['content']['repository']['nameWithOwner']='other/repo'
            if self.bad=='archived':data['item']['isArchived']=True
            return json.dumps({'data':data})
        endpoint=f"repos/{r['issue']['repository']['nameWithOwner']}/issues/{r['issue']['number']}"
        self.assertIn(args[1],(endpoint,endpoint+'/comments'))
        if args[1].endswith('/comments'):
            if '--method' in args:self.comments.append(payload);return '{}'
            return json.dumps([self.comments])
        return json.dumps({'state':'open','node_id':'wrong' if self.bad=='rest' else r['issue']['id'],
                           'number':r['issue']['number'],'html_url':r['issue']['url']})

    def test_exact_routing_both_projects_review_and_blocked_idempotent(self):
        for n in (3,4):
            self.number=n
            for status in ('Human Review','Blocked'):
                self.status=status
                with closing(sqlite3.connect(self.db)) as conn, conn:conn.execute('UPDATE tasks SET status=? WHERE id=?',('blocked' if status=='Blocked' else 'review',f't{n}'))
                rows=returns.inspect_results(self.root,f'nvrenuf/{n}')
                self.assertEqual([r['task_id'] for r in rows],[f't{n}'])
                with closing(sqlite3.connect(self.db)) as conn:
                    before=[conn.execute('SELECT * FROM '+table).fetchall() for table in ('tasks','task_runs')]
                for _ in range(2):returns.return_result(self.root,f't{n}',rows[0]['snapshot_sha256'],self.reader,f'nvrenuf/{n}')
                with closing(sqlite3.connect(self.db)) as conn:
                    self.assertEqual(before,[conn.execute('SELECT * FROM '+table).fetchall() for table in ('tasks','task_runs')])
        self.assertEqual(len(self.comments),4)
        self.assertFalse(any('state' in (p or {}) for a,p in self.calls))
        with closing(sqlite3.connect(self.db)) as conn:self.assertEqual(conn.execute('SELECT count(*) FROM task_runs').fetchone()[0],2)

    def test_remote_mismatches_reject_before_any_write(self):
        self.number=4;self.status='Human Review'
        row=returns.inspect_results(self.root,'nvrenuf/4')[0]
        for self.bad in ('item','project','issue','repo','archived','closed','rest'):
            self.calls=[]
            with self.subTest(bad=self.bad),self.assertRaises(RuntimeError):
                returns.return_result(self.root,'t4',row['snapshot_sha256'],self.reader,'nvrenuf/4')
            self.assertFalse(any('--method' in a or (p or {}).get('query','').startswith('mutation') for a,p in self.calls))

    def test_wrong_selection_stale_snapshot_and_local_binding_reject(self):
        row=returns.inspect_results(self.root,'nvrenuf/4')[0]
        with self.assertRaises(RuntimeError):returns.return_result(self.root,'t4',row['snapshot_sha256'],self.reader,'nvrenuf/3')
        work=Path(row['workspace']);(work/'output.md').write_text('changed')
        with self.assertRaises(RuntimeError):returns.return_result(self.root,'t4',row['snapshot_sha256'],self.reader,'nvrenuf/4')
        self.assertEqual(self.calls,[])
        with closing(sqlite3.connect(self.db)) as conn, conn:conn.execute("UPDATE tasks SET idempotency_key='github-project:wrong' WHERE id='t4'")
        with self.assertRaisesRegex(RuntimeError,'Card/source'):returns.inspect_results(self.root,'nvrenuf/4')


class ApiTests(dashboard_tests.LaunchTests):
    def test_catalog_and_selected_import_results(self):
        with patch.object(projects,'discover_projects',return_value=[projects.get_project(key) for key in projects.PROJECTS]):
            self.assertEqual(len(self.api.github_projects(self.request)['projects']),3)
        for selector in projects.PROJECTS:
            self.request.query_params={'project':selector}
            with patch.object(intake,'run_intake',return_value={}) as run:
                self.api.github_intake(self.request);run.assert_called_once_with(self.root,selector=selector)
            with patch.object(returns,'inspect_results',return_value=[]) as inspect:
                self.api.github_results(self.request);inspect.assert_called_once_with(self.root,selector=selector)
        self.request.query_params={'project':'nvrenuf/99'}
        with patch.object(intake,'run_intake') as run, self.assertRaises(Exception):self.api.github_intake(self.request)
        run.assert_not_called()


if __name__=='__main__':unittest.main(verbosity=2)
