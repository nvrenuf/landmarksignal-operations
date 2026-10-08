"""Discover nvrenuf's open Projects without changing historical source identities."""
import hashlib
import json
import re
import subprocess

OWNER = 'nvrenuf'
REQUIRED_STATUS = ('Queued for Jeeves', 'Human Review', 'Blocked', 'Done')
PROJECTS = {
    'nvrenuf/3': {'owner': OWNER, 'number': 3, 'id': 'PVT_kwHOAFD_484BlSRq',
                  'title': 'LandmarkSignal'},
    'nvrenuf/4': {'owner': OWNER, 'number': 4, 'id': 'PVT_kwHOAFD_484BmKAG',
                  'title': 'Hermes Optimization'},
}
_discovered = {}
DEFAULT_PROJECT = 'nvrenuf/3'
ISSUE_URL = re.compile(r'^https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)$')
DISCOVERY_QUERY = '''query($owner:String!,$cursor:String){user(login:$owner){login
  projectsV2(first:100,after:$cursor){pageInfo{hasNextPage endCursor}
    nodes{id number title closed owner{... on User{login}}
      fields(first:100){pageInfo{hasNextPage}
        nodes{... on ProjectV2SingleSelectField{id name options{id name}}}}}}}}'''


def gh(arguments, payload=None):
    try:
        result = subprocess.run(['gh', *arguments],
            input=json.dumps(payload) if payload is not None else None,
            capture_output=True, text=True, encoding='utf-8', timeout=90)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError('GitHub is unavailable (' + type(error).__name__ +
                           '). Check network access and the gh CLI installation.') from None
    if result.returncode:
        # stderr can contain credentials or proxy diagnostics; never display it.
        raise RuntimeError('GitHub request failed (exit %s). Check gh auth status and the required project scope, then Refresh projects.' % result.returncode)
    return result.stdout


def discover_projects(reader=gh):
    """Read every project page. Publish a new catalog only after complete validation."""
    if reader(['api', 'user', '--jq', '.login']).strip() != OWNER:
        raise RuntimeError('GitHub must authenticate as nvrenuf. Run gh auth status, then Refresh projects.')
    found, ids, seen_cursors, cursor = {}, set(), set(), None
    for _ in range(100):
        try:
            response = json.loads(reader(['api', 'graphql', '--input', '-'],
                {'query': DISCOVERY_QUERY, 'variables': {'owner': OWNER, 'cursor': cursor}}))
        except (ValueError, KeyError, TypeError):
            raise RuntimeError('GitHub returned an unreadable project catalog. Check network/authentication, then Refresh projects.') from None
        if response.get('errors'):
            raise RuntimeError('GitHub project discovery failed. Check gh auth status and project-read scope, then Refresh projects.')
        user = (response.get('data') or {}).get('user') or {}
        if user.get('login') != OWNER:
            raise RuntimeError('GitHub project owner identity differs; no projects were selected')
        connection = user.get('projectsV2') or {}
        for project in connection.get('nodes') or []:
            if not project or project.get('closed') is not False:
                continue
            number, project_id = project.get('number'), project.get('id')
            if (type(number) is not int or number < 1 or not isinstance(project_id, str)
                    or not project_id or (project.get('owner') or {}).get('login') != OWNER):
                raise RuntimeError('GitHub returned an invalid open project identity')
            selector = f'{OWNER}/{number}'
            if selector in found or project_id in ids:
                raise RuntimeError('GitHub returned duplicate project identities')
            if selector in PROJECTS and PROJECTS[selector]['id'] != project_id:
                raise RuntimeError('Historical Project #%s identity differs; no catalog change made' % number)
            fields = project.get('fields') or {}
            if (fields.get('pageInfo') or {}).get('hasNextPage'):
                raise RuntimeError('Project #%s fields are truncated; no catalog change made' % number)
            status = [f for f in fields.get('nodes') or [] if f and f.get('name') == 'Status']
            options = [o.get('name') for o in status[0].get('options') or []] if len(status) == 1 else []
            missing = [name for name in REQUIRED_STATUS if options.count(name) != 1]
            found[selector] = {'owner': OWNER, 'number': number, 'id': project_id,
                               'title': project.get('title') or f'Project #{number}',
                               'status_ready': len(status) == 1 and not missing,
                               'missing_status': missing if len(status) == 1 else ['Status field'],
                               'selector': selector,
                               'url': f'https://github.com/users/{OWNER}/projects/{number}'}
            ids.add(project_id)
        page = connection.get('pageInfo') or {}
        if page.get('hasNextPage') is False:
            _discovered.clear()
            _discovered.update(found)
            return sorted(found.values(), key=lambda p: (p['number'] not in (3, 4), p['number']))
        next_cursor = page.get('endCursor')
        if not next_cursor or next_cursor == cursor or next_cursor in seen_cursors:
            raise RuntimeError('GitHub project pagination stopped advancing; no catalog change made')
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    raise RuntimeError('GitHub project pagination exceeded 100 pages; no catalog change made')


def get_project(selector=DEFAULT_PROJECT):
    if not isinstance(selector, str):
        raise RuntimeError('Unsupported GitHub source project')
    project = _discovered.get(selector) or PROJECTS.get(selector)
    if not project:
        raise RuntimeError('Project is not in the discovered catalog; Refresh projects and select an open nvrenuf project')
    return {**project, 'selector': selector,
            'url': f"https://github.com/users/{project['owner']}/projects/{project['number']}"}


def require_import_status(project):
    if project.get('status_ready') is False:
        missing = ', '.join(project['missing_status'])
        raise RuntimeError('Project #%s needs existing Status options: %s. Configure them in GitHub; this launcher will not modify project fields.' % (project['number'], missing))


def validate_source(record, selector=DEFAULT_PROJECT):
    project = get_project(selector)
    issue = record.get('issue') or {}
    match = ISSUE_URL.fullmatch(issue.get('url', ''))
    if (record.get('project_owner') != project['owner']
            or type(record.get('project_number')) is not int
            or record['project_number'] != project['number']
            or record.get('project_id') != project['id']
            or not record.get('project_item_id')
            or not issue.get('id') or not match
            or match.group(1) != (issue.get('repository') or {}).get('nameWithOwner')
            or int(match.group(2)) != issue.get('number')):
        raise RuntimeError('Source project/repository/issue identity differs')
    if record.get('source_body_sha256') != hashlib.sha256((issue.get('body') or '').encode()).hexdigest():
        raise RuntimeError('Preserved source body hash differs')
    return project


def source_selector(record):
    return f"{record.get('project_owner')}/{record.get('project_number')}"


def source_key(record):
    project = validate_source(record, source_selector(record))
    # Keep the historical Project #3 namespace and workspace hashes exactly.
    prefix = 'github-project3:' if project['selector'] == DEFAULT_PROJECT else 'github-project:'
    return prefix + project['id'] + ':' + record['issue']['id']
