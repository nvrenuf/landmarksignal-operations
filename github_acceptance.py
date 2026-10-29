"""Explicit human Review acceptance and retryable synchronization to GitHub."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time

from github_projects import ISSUE_URL, get_destination, get_project, validate_source
from github_queue_intake import digest, gh
from github_handoff_results import graphql, inspect_results

PR_URL = re.compile(r'^https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/pull/([1-9][0-9]*)$')
STATUS_QUERY = '''query($project:ID!,$item:ID!){project:node(id:$project){... on ProjectV2{
 id number closed owner{... on User{login}} fields(first:100){pageInfo{hasNextPage}
 nodes{... on ProjectV2SingleSelectField{id name options{id name}}}}}}
 item:node(id:$item){... on ProjectV2Item{id isArchived project{id}
 content{... on Issue{id url number repository{nameWithOwner}}}
 fieldValueByName(name:"Status"){... on ProjectV2ItemFieldSingleSelectValue{name}}}}}'''
DONE_MUTATION = '''mutation($project:ID!,$item:ID!,$field:ID!,$option:String!){
 updateProjectV2ItemFieldValue(input:{projectId:$project,itemId:$item,fieldId:$field,
 value:{singleSelectOptionId:$option}}){projectV2Item{id}}}'''


def _binding(reader, record, project):
    """Validate every remote identity and the exact existing Done option before writing."""
    match = ISSUE_URL.fullmatch(record['issue_url'])
    if not match:
        raise RuntimeError('Preserved issue URL is invalid')
    repo, number = match.groups()
    live = json.loads(reader(['api', f'repos/{repo}/issues/{number}']))
    if (live.get('node_id') != record['issue_id'] or live.get('html_url') != record['issue_url']
            or live.get('number') != int(number) or live.get('pull_request')):
        raise RuntimeError('Live repository/issue identity differs; no completion synchronized')
    data = graphql(reader, STATUS_QUERY,
                   {'project': record['project_id'], 'item': record['project_item_id']})
    remote, item = data.get('project'), data.get('item')
    if (not remote or not item or remote.get('id') != project['id']
            or remote.get('number') != project['number'] or remote.get('closed') is True
            or (remote.get('owner') or {}).get('login') != project['owner']
            or item.get('id') != record['project_item_id'] or item.get('isArchived') is not False
            or (item.get('project') or {}).get('id') != project['id']
            or (item.get('content') or {}).get('id') != record['issue_id']
            or (item['content'].get('repository') or {}).get('nameWithOwner') != repo
            or item['content'].get('number') != int(number)
            or item['content'].get('url') != record['issue_url']):
        raise RuntimeError('Exact project/item/issue binding differs; no completion synchronized')
    fields = remote.get('fields') or {}
    if (fields.get('pageInfo') or {}).get('hasNextPage'):
        raise RuntimeError('Project fields are truncated; no completion synchronized')
    statuses = [f for f in fields.get('nodes') or [] if f and f.get('name') == 'Status']
    options = [o for o in statuses[0].get('options') or [] if o.get('name') == 'Done'] if len(statuses) == 1 else []
    if len(statuses) != 1 or len(options) != 1:
        raise RuntimeError('Project needs exactly one existing Status field and Done option; configure GitHub before acceptance')
    return repo, int(number), live, item, statuses[0], options[0]


def _verify_pr(reader, repo, requirement, pr_url):
    if requirement not in ('required', 'not_required'):
        raise RuntimeError('Choose whether a PR merge is required before accepting')
    if requirement == 'not_required':
        if pr_url:
            raise RuntimeError('A PR URL was supplied; choose Merge required and verify it')
        return None
    match = PR_URL.fullmatch(pr_url or '')
    if not match or match.group(1) != repo:
        raise RuntimeError('Required PR must be an exact pull-request URL in the originating repository')
    pr = json.loads(reader(['api', f'repos/{repo}/pulls/{match.group(2)}']))
    if (pr.get('number') != int(match.group(2)) or pr.get('html_url') != pr_url
            or not pr.get('merged_at') or not pr.get('merged')
            or ((pr.get('base') or {}).get('repo') or {}).get('full_name') != repo):
        raise RuntimeError('Required PR is not verified merged into the originating repository; do not close the issue')
    return pr_url


def _fingerprint(record):
    return digest({'task_id': record['task_id'], 'source': record['source_sha256'],
                   'run_id': record['run']['id'], 'artifacts': record['artifacts']})


def _acceptance_event(conn, record, summary, requirement, pr_url, actor):
    """Create one auditable acceptance decision, or validate its prior decision on retry."""
    fingerprint = _fingerprint(record)
    marker = '<!-- landmarksignal-human-acceptance:v1:' + hashlib.sha256(
        (record['task_id'] + ':' + fingerprint).encode()).hexdigest() + ' -->'
    row = conn.execute("SELECT payload FROM task_events WHERE task_id=? AND kind='human_accepted' ORDER BY id DESC LIMIT 1",
                       (record['task_id'],)).fetchone()
    if row:
        previous = json.loads(row[0])
        if any(previous.get(k) != v for k, v in {
                'fingerprint': fingerprint, 'summary': summary,
                'pr_requirement': requirement, 'pr_url': pr_url or '',
                'actor': actor, 'marker': marker}.items()):
            raise RuntimeError('A different human acceptance is already recorded; review the task event before retrying')
        return previous
    if record['status'] != 'review':
        raise RuntimeError('Only an original intake root in Review can receive new human acceptance')
    event = {'fingerprint': fingerprint, 'summary': summary,
             'pr_requirement': requirement, 'pr_url': pr_url or '', 'actor': actor,
             'marker': marker, 'accepted_at': datetime.now(timezone.utc).isoformat(),
             'source_sha256': record['source_sha256'],
             'project_id': record['project_id'], 'project_item_id': record['project_item_id'],
             'issue_id': record['issue_id'], 'run_id': record['run']['id'],
             'method': 'Jeeves dashboard Accept & Complete',
             'evidence_record': record}
    conn.execute('BEGIN IMMEDIATE')
    try:
        current = conn.execute('SELECT status FROM tasks WHERE id=?', (record['task_id'],)).fetchone()
        if not current or current[0] != 'review':
            raise RuntimeError('Task left Review; refresh before accepting')
        if conn.execute("SELECT count(*) FROM task_events WHERE task_id=? AND kind='human_accepted'",
                        (record['task_id'],)).fetchone()[0]:
            raise RuntimeError('Another human acceptance was recorded; refresh before retrying')
        conn.execute('INSERT INTO task_events(task_id,kind,payload,created_at) VALUES (?, ?, ?, ?)',
                     (record['task_id'], 'human_accepted', json.dumps(event, sort_keys=True), int(time.time())))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return event


def _comment_body(record, event):
    run = record['run']
    artifact_lines = '\n'.join('- ' + a['name'] + ' — SHA256 ' + a['sha256'] for a in record['artifacts'])
    return (event['marker'] + '\n## Human acceptance and completion evidence\n\n'
            + 'Accepted by ' + event['actor'] + ' through ' + event['method'] + ' at ' + event['accepted_at'] + '.\n'
            + 'Decision: ' + event['summary'] + '\n'
            + 'PR merge: ' + (event['pr_url'] if event['pr_requirement'] == 'required' else 'Human marked no PR merge required') + '\n\n'
            + 'Board: ' + record['board'] + '\nTask: ' + record['task_id'] + '\nRun: ' + str(run['id'])
            + '\nProfile: ' + str(run.get('profile')) + '\nWorkspace: `' + record['workspace'] + '`\n'
            + 'Source snapshot SHA256: ' + record['source_sha256'] + '\n\n'
            + 'Worker outcome: ' + str(run.get('outcome')) + '\n'
            + 'Worker summary: ' + str(run.get('summary') or 'No worker summary recorded')[:6000]
            + '\n\nArtifact inventory:\n' + (artifact_lines or 'No local .py/.md artifacts listed.') + '\n')


def accept_complete(root, task_id, snapshot_sha256, summary, pr_requirement, pr_url='',
                    phrase='', reader=gh, selector=None, complete=None):
    """Preflight, record acceptance, complete native Review, then sync GitHub idempotently."""
    if not selector:
        raise RuntimeError('Select the exact originating project')
    project = get_project(selector)
    destination = get_destination(selector)
    rows = [r for r in inspect_results(root, selector) if r['task_id'] == task_id]
    if len(rows) != 1 or rows[0]['snapshot_sha256'] != snapshot_sha256:
        raise RuntimeError('Task or evidence changed; refresh results before accepting')
    record = rows[0]
    if record['board'] != destination['board'] or record['project_selector'] != selector:
        raise RuntimeError('Board or selected project differs')
    if phrase != 'ACCEPT ' + task_id:
        raise RuntimeError('Type ACCEPT and the exact task ID to record human acceptance')
    summary = (summary or '').strip()
    if not summary or len(summary) > 2000:
        raise RuntimeError('Provide a human acceptance summary of 1–2000 characters')
    if record.get('required_pr_merge') and pr_requirement != 'required':
        raise RuntimeError('The preserved source requires a merged PR; choose Merged PR required')
    if reader(['api', 'user', '--jq', '.login']).strip() != project['owner']:
        raise RuntimeError('GitHub account must be nvrenuf before acceptance')
    repo, number, live, item, field, done_option = _binding(reader, record, project)
    verified_pr = _verify_pr(reader, repo, pr_requirement, (pr_url or '').strip())
    database = root / 'kanban/boards' / destination['board'] / 'kanban.db'
    with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=rw', uri=True, timeout=10)) as conn:
        conn.row_factory = sqlite3.Row
        contract_row = conn.execute('SELECT completion_contract FROM tasks WHERE id=?', (task_id,)).fetchone()
        if not contract_row:
            raise RuntimeError('Native task disappeared; refresh before accepting')
        if contract_row['completion_contract'] not in (None, '', 'local-only') and pr_requirement != 'required':
            raise RuntimeError('The native task requires a merged PR; choose Merged PR required')
        existing = conn.execute("SELECT payload FROM task_events WHERE task_id=? AND kind='human_accepted' ORDER BY id DESC LIMIT 1",
                                (task_id,)).fetchone()
        if live.get('state') != 'open' and not existing:
            raise RuntimeError('Issue was already closed without this acceptance; review it in GitHub')
        event = _acceptance_event(conn, record, summary, pr_requirement, verified_pr, project['owner'])
        if record['status'] == 'review':
            if complete is None:
                from hermes_cli import kanban_db
                complete = kanban_db.complete_task
            metadata = {'human_acceptance': {'marker': event['marker'],
                                             'actor': event['actor'],
                                             'accepted_at': event['accepted_at']}}
            if verified_pr:
                metadata['published_pr'] = verified_pr
            if not complete(conn, task_id, result=summary, summary=summary,
                            metadata=metadata, force=True):
                raise RuntimeError('Human acceptance recorded, but native Review → Done was refused. Resolve dependencies and retry; GitHub was untouched.')
        elif record['status'] != 'done':
            raise RuntimeError('Accepted task is neither Review nor Done; GitHub was untouched')
    # Evidence MUST precede Project Done: an existing GitHub workflow can close the issue on Done.
    try:
        pages = json.loads(reader(['api', f'repos/{repo}/issues/{number}/comments', '--paginate', '--slurp']))
        if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
            raise RuntimeError('Issue comment pagination was incomplete')
        if not any(event['marker'] in c.get('body', '') for page in pages for c in page):
            reader(['api', f'repos/{repo}/issues/{number}/comments', '--method', 'POST', '--input', '-'],
                   {'body': _comment_body(record, event)})
    except Exception as error:
        raise RuntimeError('Human acceptance and native Done are recorded; GitHub evidence comment failed (' +
                           type(error).__name__ + '). Retry Sync completion; no duplicate comment will be posted.') from None
    try:
        if ((item.get('fieldValueByName') or {}).get('name')) != 'Done':
            graphql(reader, DONE_MUTATION, {'project': project['id'], 'item': record['project_item_id'],
                                            'field': field['id'], 'option': done_option['id']})
        # Re-read the exact item after any GitHub workflow has run.
        _, _, live_after, item_after, _, _ = _binding(reader, record, project)
        if (item_after.get('fieldValueByName') or {}).get('name') != 'Done':
            raise RuntimeError('Project Done was not verified')
    except Exception as error:
        raise RuntimeError('Acceptance evidence is posted; project Done failed or could not be verified (' +
                           type(error).__name__ + '). Retry Sync completion.') from None
    try:
        if live_after.get('state') == 'open':
            reader(['api', f'repos/{repo}/issues/{number}', '--method', 'PATCH', '--input', '-'],
                   {'state': 'closed'})
        final = json.loads(reader(['api', f'repos/{repo}/issues/{number}']))
        if final.get('state') != 'closed' or final.get('node_id') != record['issue_id']:
            raise RuntimeError('Issue closure was not verified')
    except Exception as error:
        raise RuntimeError('Evidence posted and Project Done verified; issue closure failed or could not be verified (' +
                           type(error).__name__ + '). Retry Sync completion; closed issues will not be reopened.') from None
    return {'task_id': task_id, 'issue_url': record['issue_url'], 'status': 'Done',
            'acceptance_verified': True, 'issue_closed': True, 'marker': event['marker']}
