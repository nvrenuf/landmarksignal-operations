"""Stable issue identity and real native execution binding."""
import hashlib
import json
from pathlib import Path


def compute_sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def identity(record):
    return record['github_repo'], record['github_issue_url']


def is_duplicate(existing_records, new_record):
    return any(identity(r) == identity(new_record) for r in existing_records)


def extract_github_metadata(source):
    issue = source['issue']
    return dict(github_repo=issue['repository']['nameWithOwner'], github_issue_url=issue['url'],
                github_issue_number=issue['number'], github_issue_title=issue['title'],
                github_issue_body=issue.get('body') or '', github_issue_body_sha256=compute_sha256(issue.get('body') or ''),
                github_status=source['source_status'], board_name='landmarksignal',
                github_blockers=source.get('github_blockers', []),
                priority=source.get('project_fields', {}).get('Priority'),
                execution_order=source.get('project_fields', {}).get('Execution Order'),
                sprint=source.get('project_fields', {}).get('Sprint'),
                **{k:source.get(k) for k in ('project_id','project_item_id','project_number','project_owner')})


def create_hermes_record(metadata, run_info):
    required = ('task_id','run_id','profile','workspace_path')
    if any(run_info.get(k) is None or run_info.get(k) == '' for k in required):
        raise ValueError('Actual native task/run/profile/workspace binding is required')
    if str(run_info['task_id']).startswith('t_placeholder') or int(run_info['run_id']) <= 0:
        raise ValueError('Placeholder execution binding is invalid')
    return {**metadata, 'board_name':'landmarksignal', 'hermes_task_id':run_info['task_id'],
            'hermes_run_id':run_info['run_id'], 'assigned_profile':run_info['profile'],
            'workspace_path':run_info['workspace_path'], 'approval_record':run_info.get('approval_record'),
            'status':run_info.get('status'), 'outcome':run_info.get('outcome'), 'artifacts':[]}


def load_existing_records(path):
    if not Path(path).exists(): return []
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    return data if isinstance(data,list) else data['records']


def save_record(path, record):
    records=load_existing_records(path)
    for i, old in enumerate(records):
        if identity(old)==identity(record):
            records[i]=record
            break
    else: records.append(record)
    Path(path).write_text(json.dumps({'records':records},indent=2),encoding='utf-8')


def process_github_source(source_path, run_info=None):
    if run_info is None: raise ValueError('Supply actual native run information; intake is not approval')
    return create_hermes_record(extract_github_metadata(json.loads(Path(source_path).read_text(encoding='utf-8'))),run_info)
