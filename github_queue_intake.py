"""Manual, read-only GitHub Project #3 queue intake into native Hermes Triage.

No model, specification, task claim, dispatcher, assignment or GitHub write.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import uuid

OWNER = 'nvrenuf'
PROJECT = 3
QUEUED = 'Queued for Jeeves'
REVISION = '0c2ff854a5c5121c75ac0b0a35241a580ee27fb7'
QUERY = '''query($owner:String!, $number:Int!, $cursor:String) {
  user(login:$owner) { projectV2(number:$number) { id title
    items(first:100, after:$cursor) { pageInfo { hasNextPage endCursor }
      nodes { id isArchived content { __typename ... on Issue {
        id number url title body updatedAt state repository { nameWithOwner }
      } } fieldValues(first:100) { pageInfo { hasNextPage }
        nodes { ... on ProjectV2ItemFieldSingleSelectValue { name field {
          ... on ProjectV2SingleSelectField { name }
        } }
        ... on ProjectV2ItemFieldNumberValue { number field { ... on ProjectV2Field { name } } }
        ... on ProjectV2ItemFieldTextValue { text field { ... on ProjectV2Field { name } } }
        ... on ProjectV2ItemFieldIterationValue { title field { ... on ProjectV2IterationField { name } } }
      } } }
    }
  } }
}'''
ISSUE_URL = re.compile(r'^https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)$')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def gh(arguments, payload=None):
    result = subprocess.run(['gh', *arguments], input=json.dumps(payload) if payload is not None else None,
                            capture_output=True, text=True, encoding='utf-8', timeout=90)
    if result.returncode:
        # CLI stderr may contain credentials or proxy diagnostics. Do not echo it.
        raise RuntimeError('GitHub read failed (exit %s). Check gh authentication/project-read scope.' % result.returncode)
    return result.stdout


def read_queue(reader=gh):
    if reader(['api', 'user', '--jq', '.login']).strip() != OWNER:
        raise RuntimeError('GitHub must authenticate as nvrenuf; no card created')
    result, seen, cursor = [], set(), None
    for _ in range(100):
        value = json.loads(reader(['api', 'graphql', '--input', '-'],
                                 {'query': QUERY, 'variables': {'owner': OWNER, 'number': PROJECT, 'cursor': cursor}}))
        if value.get('errors'):
            raise RuntimeError('GitHub Project read failed; no card created')
        project = ((value.get('data') or {}).get('user') or {}).get('projectV2')
        if not project or not project.get('id'):
            raise RuntimeError('Existing nvrenuf Project #3 is unavailable')
        items = project['items']
        for item in items['nodes']:
            if item.get('isArchived'):
                continue
            fields = item['fieldValues']
            if fields['pageInfo']['hasNextPage']:
                raise RuntimeError('Project fields are truncated; nothing imported')
            statuses = [v['name'] for v in fields['nodes'] if v.get('field', {}).get('name') == 'Status']
            if statuses != [QUEUED]:
                continue
            issue = item.get('content') or {}
            if issue.get('__typename') != 'Issue' or issue.get('state') != 'OPEN':
                continue
            match = ISSUE_URL.fullmatch(issue.get('url', ''))
            if (not match or match.group(1) != issue['repository']['nameWithOwner']
                    or int(match.group(2)) != issue['number']):
                raise RuntimeError('Queued issue identity differs; nothing imported')
            if issue['id'] in seen:
                continue
            seen.add(issue['id'])
            result.append({'project_id': project['id'], 'project_item_id': item['id'],
                           'project_number': PROJECT, 'project_owner': OWNER,
                           'source_status': QUEUED, 'issue': issue,
                           'project_fields': {v['field']['name']: next((v[k] for k in ('name','number','text','title') if k in v), None)
                                              for v in fields['nodes'] if v.get('field',{}).get('name') in ('Priority','Execution Order','Sprint')}})
        page = items['pageInfo']
        if not page['hasNextPage']:
            break
        if not page['endCursor'] or page['endCursor'] == cursor:
            raise RuntimeError('Project pagination did not advance')
        cursor = page['endCursor']
    else:
        raise RuntimeError('Project pagination limit reached; nothing imported')
    # Read all dependency pages before any board changes; never treat a read failure as no dependencies.
    for record in result:
        issue = record['issue']
        endpoint = 'repos/%s/issues/%s/dependencies/blocked_by' % (issue['repository']['nameWithOwner'], issue['number'])
        pages = json.loads(reader(['api', endpoint, '--paginate', '--slurp']))
        if not isinstance(pages, list) or any(not isinstance(p, list) for p in pages):
            raise RuntimeError('Dependency response is incomplete')
        record['github_blockers'] = [{'url': v['html_url'], 'title': v['title'], 'state': v['state']}
                                     for page in pages for v in page]
        record['source_body_sha256'] = hashlib.sha256((issue.get('body') or '').encode()).hexdigest()
    return result


def key(record):
    return 'github-project3:' + record['project_id'] + ':' + record['issue']['id']


def body(record, source_path):
    issue = record['issue']
    deps = record['github_blockers']
    return ('# GitHub work selected for Triage\n\nSource: ' + issue['url']
            + '\nProject: https://github.com/nvrenuf/projects/3\nSource updated: ' + issue['updatedAt']
            + '\nOriginal body SHA256: ' + record['source_body_sha256']
            + '\nSource snapshot: ' + str(source_path)
            + '\n\nIntake authorizes planning only. This card has not been approved for execution.\n'
            + '\n## GitHub blocking dependencies\n'
            + ('\n'.join('- %s (%s): %s' % (v['url'], v['state'], v['title']) for v in deps)
               if deps else 'No structured GitHub blockers recorded. Check the original requirements for other dependencies.')
            + '\n\n## Original GitHub requirements (preserve during specification)\n\n'
            + (issue.get('body') or '(No body; clarification required.)') + '\n')


def import_records(conn, kb, records, work_root):
    """All native card creations in one transaction; pre-existing cards remain byte-for-byte equal."""
    conn.row_factory = sqlite3.Row
    before = {r['id']: dict(r) for r in conn.execute('SELECT * FROM tasks')}
    if any(r['status'] == 'running' for r in before.values()):
        raise RuntimeError('A LandmarkSignal task is running; wait before intake')
    created, existing, skipped = [], [], []
    conn.execute('BEGIN IMMEDIATE')
    try:
        for record in records:
            url = record['issue']['url']
            matches = [r for r in before.values() if r.get('idempotency_key') == key(record)
                       or (r.get('body') or '').split('\n', 1)[0].strip() == url
                       or re.search(r'^Source: ' + re.escape(url) + r'$', r.get('body') or '', re.MULTILINE)]
            if len(matches) > 1:
                skipped.append({'issue_url': url, 'reason': 'Multiple existing linked cards; review before importing'})
                continue
            if matches:
                existing.append({'issue_url': url, 'task_id': matches[0]['id'], 'status': matches[0]['status']})
                continue
            workspace = work_root / hashlib.sha256(key(record).encode()).hexdigest()[:24]
            workspace.mkdir(parents=True, exist_ok=True)
            source_path = workspace / 'github-source.json'
            if source_path.exists():
                old = json.loads(source_path.read_text(encoding='utf-8'))
                if digest(old) != digest(record):
                    skipped.append({'issue_url': url, 'reason': 'Preserved source differs; review before importing'})
                    continue
            else:
                with source_path.open('x', encoding='utf-8', newline='\n') as stream:
                    json.dump(record, stream, indent=2, ensure_ascii=False)
            task_id = kb.create_task(conn, title='Issue #%s: %s' % (record['issue']['number'], record['issue']['title']),
                body=body(record, source_path), triage=True, initial_status='running', assignee=None,
                created_by='Lee manual GitHub queue intake', workspace_kind='dir', workspace_path=str(workspace),
                project_id='', board='landmarksignal', idempotency_key=key(record), max_retries=0)
            card = dict(conn.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone())
            if card['status'] != 'triage' or card.get('assignee') or card.get('claim_lock') or card.get('worker_pid'):
                raise RuntimeError('Native card did not remain unclaimed Triage')
            created.append({'issue_url': url, 'task_id': task_id, 'status': 'triage'})
        after = {r['id']: dict(r) for r in conn.execute('SELECT * FROM tasks')}
        if any(after.get(task_id) != row for task_id, row in before.items()):
            raise RuntimeError('Pre-existing card changed; intake rolled back')
        if set(after) != set(before) | {v['task_id'] for v in created}:
            raise RuntimeError('Unexpected task creation; intake rolled back')
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return {'created': created, 'existing': existing, 'skipped': skipped,
            'original_cards_preserved': True, 'execution_authorized': False}


def run_intake(root):
    from execution_guard_v1_final import ExecutionGuard
    from hermes_cli import kanban_db as kb
    batch = root / 'landmarksignal-v1/intake' / uuid.uuid4().hex
    def apply():
        records = read_queue()
        board = root / 'kanban/boards/landmarksignal/kanban.db'
        if not board.is_file():
            raise RuntimeError('Existing LandmarkSignal board is missing')
        batch.mkdir(parents=True)
        with closing(sqlite3.connect(board.resolve().as_uri() + '?mode=ro', uri=True, timeout=10)) as source, closing(sqlite3.connect(batch / 'board.before.db')) as backup:
            source.backup(backup)
        # Existing SQLite connection is pinned explicitly; native create_task supplies card/event semantics. No schema init or migration.
        with closing(sqlite3.connect(board.resolve().as_uri() + '?mode=rw', uri=True, timeout=10)) as conn:
            result = import_records(conn, kb, records, root / 'landmarksignal-v1/work/github-intake')
        result.update(project_url='https://github.com/nvrenuf/projects/3', queued_count=len(records),
                      batch_id=batch.name, backup=str(batch / 'board.before.db'),
                      completed_at=datetime.now(timezone.utc).isoformat(),
                      specification_run=False, model_calls=0, tasks_dispatched=0)
        (batch / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        return result
    return ExecutionGuard('9', 'github-queue-intake', timeout=0).execute(apply)
