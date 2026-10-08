import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
if os.name == 'nt':
    sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'hermes/hermes-agent'))
    import hermes_bootstrap
sys.path.insert(0,str(Path(__file__).parent/'issue9'))
import handoff_logic as handoff
import sprint_assignment as sprint
import status_sync as sync
import evidence_mechanism as evidence
import github_handoff_results as returns
import landmarksignal_review_policy as policy
from install_issue9_workflow import prepare_config, apply_changes

class WorkflowTests(unittest.TestCase):
    def test_queue_never_maps_to_execution_and_done_requires_human_review(self):
        self.assertEqual(sync.map_github_status_to_hermes('Queued for Jeeves'),'triage')
        for status in ('done','review'):self.assertEqual(sync.map_hermes_status_to_github(status),'Human Review')
        self.assertEqual(sync.map_hermes_status_to_github('running'),'In Progress')
        self.assertEqual(sync.map_hermes_status_to_github('blocked'),'Blocked')
    def test_sprint_plan_preserves_human_values_without_mutating_input(self):
        r={'priority':'P1','execution_order':8,'sprint':'Sprint 001','updated_at':'2026-10-08T00:00:00Z'}
        plan=sprint.generate_sprint_plan([r]);self.assertEqual(plan['sprint_breakdown'],{'Sprint 001':1})
        self.assertNotIn('sprint_assignment',r);self.assertEqual(plan['sprints']['Sprint 001'][0]['execution_order'],8)
    def test_missing_wrong_issue_or_nonboolean_approval_rejected(self):
        for r in ({},{'status':'ready'},{'status':'blocked'},{'status':'done'}):self.assertFalse(sprint.verify_unauthorized_dispatch(r)[0])
        r={'status':'ready','hermes_task_id':'t_x','github_issue_url':'issue9','approval_record':{'approved':True,'approval_type':'manual','approved_by':'Lee','approved_at':'now','issue_url':'issue9','task_id':'t_x'}}
        self.assertTrue(sprint.verify_unauthorized_dispatch(r)[0]);r['approval_record']['issue_url']='issue7';self.assertFalse(sprint.verify_unauthorized_dispatch(r)[0])
    def test_changed_body_remains_same_issue_and_binding_is_not_invented(self):
        a={'github_repo':'repo','github_issue_url':'url','github_issue_body_sha256':'a'}
        self.assertTrue(handoff.is_duplicate([a],{**a,'github_issue_body_sha256':'b'}))
        with self.assertRaises(ValueError):handoff.create_hermes_record(a,{})
    def test_repeat_return_records_are_stable_and_status_changes_not_lost(self):
        with tempfile.TemporaryDirectory() as folder:
            s=sync.StatusSynchronizer(str(Path(folder)/'records.json'));r={'hermes_task_id':'t_1','hermes_run_id':1}
            first=s.sync_hermes_to_github(r,'url',[],'running')
            self.assertEqual(first,s.sync_hermes_to_github(r,'url',[],'running'))
            self.assertEqual(s.sync_hermes_to_github(r,'url',[],'review')['github_status_after'],'Human Review')
            self.assertEqual(len(s.records),2)
    def test_failure_and_review_evidence_are_retained(self):
        r=evidence.ExecutionRecord('t_1','Title','blocked','jeeves','workspace',kanban_run_id='42')
        r.attach_evidence(evidence.Evidence(type='failure_log',details='failure'))
        r.attach_evidence(evidence.Evidence(type='human_review',details='pending'))
        result=evidence.get_github_return_payload(r)
        self.assertEqual(len(result['evidence']),2);self.assertEqual(result['kanban_run_id'],'42')
    def test_workers_can_work_but_cannot_self_complete(self):
        with patch.dict(os.environ,{'HERMES_KANBAN_BOARD':'landmarksignal'}):
            self.assertEqual(policy.decide('kanban_complete',{})['action'],'block')
            for tool in ('kanban_show','kanban_request_review','kanban_block','terminal','write_file'):
                self.assertIsNone(policy.decide(tool,{}))
        with patch.dict(os.environ,{'HERMES_KANBAN_BOARD':'other','HERMES_KANBAN_DB':''}):self.assertIsNone(policy.decide('kanban_complete',{'board':'other'}))
    def test_config_preserves_model_approvals_unknown_keys_and_is_repeatable(self):
        import yaml
        original=b'model:\r\n  default: Qwen\r\napprovals:\r\n  mode: manual\r\nkanban:\r\n  review_dispatch: true\r\n  custom_key: keep\r\nplugins:\r\n  enabled: [landmarksignal-launch]\r\n'
        new=prepare_config(original,True);a=yaml.safe_load(original);b=yaml.safe_load(new)
        self.assertEqual(a['model'],b['model']);self.assertEqual(a['approvals'],b['approvals']);self.assertEqual(b['kanban']['custom_key'],'keep')
        self.assertIs(b['kanban']['review_dispatch'],False);self.assertEqual(new,prepare_config(new,True))
    def test_install_failure_restores_files_and_retains_backups(self):
        import install_issue9_workflow as installer
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);one=root/'one';two=root/'two';one.write_bytes(b'original');two.write_bytes(b'second')
            original={one:b'original',two:b'second'};calls=[];real=installer.replace
            def fail_once(path,value):
                calls.append(path)
                if len(calls)==2:raise PermissionError('simulated protected file')
                return real(path,value)
            with patch.object(installer,'replace',fail_once), self.assertRaises(PermissionError):
                apply_changes({one:b'new',two:b'new2'},original,root/'backup')
            self.assertEqual(one.read_bytes(),b'original');self.assertEqual(two.read_bytes(),b'second')
            self.assertTrue(list((root/'backup').glob('*/0.before')))
    def test_return_reads_actual_native_run_and_is_idempotent_and_never_closes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);work=root/'landmarksignal-v1/work/github-intake/abc';work.mkdir(parents=True)
            (work/'github-source.json').write_text(json.dumps({'project_owner':'nvrenuf','project_number':3,'project_id':'P3','project_item_id':'PI9','issue':{'url':'https://github.com/nvrenuf/landmarksignal-operations/issues/9'}}))
            (work/'test.py').write_text('print("test")')
            db=root/'kanban/boards/landmarksignal/kanban.db';db.parent.mkdir(parents=True)
            c=sqlite3.connect(db);c.executescript('CREATE TABLE tasks(id,title,status,workspace_path,idempotency_key); CREATE TABLE task_runs(id,task_id,profile,outcome,summary);')
            c.execute('INSERT INTO tasks VALUES (?,?,?,?,?)',('t_root','Issue9','done',str(work),'github-project3:P3:I9'))
            c.execute('INSERT INTO task_runs VALUES (?,?,?,?,?)',(42,'t_root','jeeves','completed','worker summary'));c.commit();c.close()
            result=returns.inspect_results(root)[0];self.assertEqual(result['run']['id'],42)
            calls=[];comments=[]
            def reader(args,payload=None):
                calls.append((args,payload))
                if args[1]=='user':return 'nvrenuf'
                if args[1]=='graphql':
                    q=payload['query']
                    if q.startswith('mutation'):return json.dumps({'data':{'updateProjectV2ItemFieldValue':{'projectV2Item':{'id':'PI9'}}}})
                    if 'fieldValueByName' in q:return json.dumps({'data':{'node':{'fieldValueByName':{'name':'Human Review'}}}})
                    return json.dumps({'data':{'project':{'id':'P3','number':3,'owner':{'login':'nvrenuf'},'fields':{'pageInfo':{'hasNextPage':False},'nodes':[{'id':'STATUS','name':'Status','options':[{'id':'REVIEW','name':'Human Review'}]}]}},'item':{'project':{'id':'P3'},'content':{'url':result['issue_url']}}}})
                if args[1].endswith('/comments'):
                    if '--method' in args:comments.append(payload);return '{}'
                    return json.dumps([comments])
                return '{"state":"open"}'
            for _ in range(2):self.assertEqual(returns.return_result(root,'t_root',result['snapshot_sha256'],reader)['status'],'Human Review')
            self.assertEqual(len(comments),1)
            self.assertFalse(any('state' in (p or {}) for a,p in calls))
            self.assertTrue(all(p['variables']['field']=='STATUS' for a,p in calls if p and p.get('query','').startswith('mutation')))

if __name__=='__main__':unittest.main(verbosity=2)
