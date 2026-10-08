"""Explicitly approved GitHub user projects; IDs verified October 8, 2026."""
import hashlib
import re

PROJECTS = {
    'nvrenuf/3': {'owner': 'nvrenuf', 'number': 3, 'id': 'PVT_kwHOAFD_484BlSRq',
                  'title': 'LandmarkSignal'},
    'nvrenuf/4': {'owner': 'nvrenuf', 'number': 4, 'id': 'PVT_kwHOAFD_484BmKAG',
                  'title': 'Hermes Optimization'},
}
DEFAULT_PROJECT = 'nvrenuf/3'
ISSUE_URL = re.compile(r'^https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)$')


def get_project(selector=DEFAULT_PROJECT):
    if not isinstance(selector, str) or selector not in PROJECTS:
        raise RuntimeError('Unsupported GitHub source project')
    project = PROJECTS[selector]
    return {**project, 'selector': selector,
            'url': f"https://github.com/users/{project['owner']}/projects/{project['number']}"}


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
