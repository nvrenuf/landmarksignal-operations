"""Preserve human-selected sprint, priority and execution order."""
from copy import deepcopy
from datetime import datetime
PRIORITY_ORDER={'P0':0,'P1':1,'P2':2,'P3':3}


def parse_priority(priority):
    return PRIORITY_ORDER.get(str(priority).upper(),3)


def compute_sort_key(record):
    order=record.get('execution_order')
    return parse_priority(record.get('priority')), float(order) if order is not None else float('inf')


def get_sprint_number(sprint, execution_order=None):
    return sprint  # Sprint is selected by Lee, never inferred from priority.


def assign_to_sprint(records, selected_sprint=None):
    result=sorted(deepcopy(records),key=compute_sort_key)
    for record in result:
        record['sprint_assignment']=record.get('sprint') if selected_sprint is None else selected_sprint
    return result


def verify_unauthorized_dispatch(record):
    approval=record.get('approval_record') or {}
    if record.get('status') not in ('ready','running'):
        return False,'Only an eligible released task can execute'
    if approval.get('approved') is not True or approval.get('approval_type') != 'manual':
        return False,'Explicit execution approval is missing'
    if not approval.get('approved_by') or not approval.get('approved_at'):
        return False,'Approval identity/time is missing'
    if approval.get('issue_url') != record.get('github_issue_url') or approval.get('task_id') != record.get('hermes_task_id'):
        return False,'Approval does not bind this issue and task'
    return True,'Approved for the specified task; output still requires human review'


def generate_sprint_plan(records):
    sprints={}
    for r in assign_to_sprint(records):
        sprints.setdefault(str(r['sprint_assignment'] or 'Unassigned'),[]).append(r)
    return {'total_records':len(records),'sprint_breakdown':{k:len(v) for k,v in sprints.items()},'sprints':sprints}
