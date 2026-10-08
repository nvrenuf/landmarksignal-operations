"""Record proposed status returns; remote writes use the explicit dashboard return."""
import hashlib
import json
from pathlib import Path


def generate_sync_id(github_issue_url, hermes_task_id, run_id=None, status=None):
    return hashlib.sha256(json.dumps([github_issue_url,hermes_task_id,run_id,status]).encode()).hexdigest()


def map_github_status_to_hermes(status):
    if status=='Queued for Jeeves': return 'triage'
    if status=='Blocked': return 'blocked'
    return 'todo'  # A GitHub status never launches or completes an existing native task.


def map_hermes_status_to_github(status):
    mapping={'triage':'Queued for Jeeves','todo':'Queued for Jeeves','ready':'Queued for Jeeves',
             'running':'In Progress','review':'Human Review','pending_review':'Human Review',
             'done':'Human Review','blocked':'Blocked','crashed':'Blocked','failed':'Blocked'}
    if status not in mapping: raise ValueError('Unknown native status: '+str(status))
    return mapping[status]


class StatusSynchronizer:
    def __init__(self,sync_records_path):
        self.records_path=Path(sync_records_path)
        self.records=json.loads(self.records_path.read_text()).get('records',[]) if self.records_path.exists() else []
    def _record(self,url,task,status,direction,run_id=None,evidence=None):
        key=generate_sync_id(url,task,run_id,status)
        for old in self.records:
            if old.get('sync_id')==key and old.get('sync_type')==direction: return old
        r={'sync_id':key,'sync_type':direction,'github_issue_url':url,'hermes_task_id':task,'hermes_run_id':run_id,
           'hermes_status_after':map_github_status_to_hermes(status) if direction=='github_to_hermes' else status,
           'github_status_after':status if direction=='github_to_hermes' else map_hermes_status_to_github(status),
           'evidence':evidence or []}
        self.records.append(r);self.records_path.write_text(json.dumps({'records':self.records},indent=2),encoding='utf-8')
        return r
    def sync_github_to_hermes(self,github_data,hermes_task_id,hermes_status,profile,workspace_path):
        return self._record(github_data['issue']['url'],hermes_task_id,github_data['source_status'],'github_to_hermes')
    def sync_hermes_to_github(self,hermes_record,github_issue_url,evidence,status):
        return self._record(github_issue_url,hermes_record['hermes_task_id'],status,'hermes_to_github',hermes_record.get('hermes_run_id'),evidence)
    def get_sync_history(self,task): return [r for r in self.records if r['hermes_task_id']==task]
