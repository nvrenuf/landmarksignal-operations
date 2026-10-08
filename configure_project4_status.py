"""Add only the three missing options to Project #4's existing Status field."""
import argparse
import json
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from github_projects import get_project
from github_queue_intake import gh
from github_handoff_results import graphql

FIELD = 'PVTSSF_lAHOAFD_484BmKAGzhk0Hdw'
REQUIRED = ('Queued for Jeeves', 'Human Review', 'Blocked')
QUERY = '''query($id:ID!) { node(id:$id) { ... on ProjectV2 {
 id number owner { ... on User { login } }
 fields(first:100) { pageInfo { hasNextPage } nodes {
 ... on ProjectV2Field { id name dataType }
 ... on ProjectV2IterationField { id name configuration { iterations { id title startDate duration } } }
 ... on ProjectV2SingleSelectField { id name options { id name color description } }
 } }
 items(first:100) { pageInfo { hasNextPage } nodes { id isArchived
 fieldValues(first:100) { pageInfo { hasNextPage } nodes {
 ... on ProjectV2ItemFieldSingleSelectValue { name optionId field { ... on ProjectV2SingleSelectField { id } } }
 ... on ProjectV2ItemFieldNumberValue { number field { ... on ProjectV2Field { id } } }
 ... on ProjectV2ItemFieldTextValue { text field { ... on ProjectV2Field { id } } }
 ... on ProjectV2ItemFieldIterationValue { iterationId field { ... on ProjectV2IterationField { id } } }
 } } } }
 } } }'''


def prepare_options(existing):
    if len({o['name'] for o in existing}) != len(existing):
        raise RuntimeError('Ambiguous existing Status options')
    return [*existing, *[{'name':name, 'color':color, 'description':''}
            for name,color in zip(REQUIRED, ('BLUE','ORANGE','RED'))
            if name not in {o['name'] for o in existing}]]


def read(reader=gh):
    approved=get_project('nvrenuf/4')
    value=graphql(reader,QUERY,{'id':approved['id']})['node']
    if (not value or value['id']!=approved['id'] or value['number']!=4
            or value['owner'].get('login')!='nvrenuf'):
        raise RuntimeError('Project #4 identity differs')
    if (value['fields']['pageInfo']['hasNextPage'] or value['items']['pageInfo']['hasNextPage']
            or any(i['fieldValues']['pageInfo']['hasNextPage'] for i in value['items']['nodes'])):
        raise RuntimeError('Snapshot truncated; no field change')
    fields=[f for f in value['fields']['nodes'] if f.get('name')=='Status']
    if len(fields)!=1 or fields[0]['id']!=FIELD:
        raise RuntimeError('Existing Status field identity differs')
    return value,fields[0]


def configure(recovery, reader=gh):
    if reader(['api','user','--jq','.login']).strip()!='nvrenuf':
        raise RuntimeError('GitHub account must be nvrenuf')
    before,field=read(reader)
    options=prepare_options(field['options'])
    if options==field['options']:return None
    backup=Path(recovery)/('project4-status-'+uuid.uuid4().hex)
    backup.mkdir(parents=True)
    (backup/'before.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
    if read(reader)[0]!=before:raise RuntimeError('Project changed during preflight')
    mutation='''mutation($field:ID!,$options:[ProjectV2SingleSelectFieldOptionInput!]!) {
      updateProjectV2Field(input:{fieldId:$field,singleSelectOptions:$options}) {
        projectV2Field { ... on ProjectV2SingleSelectField { id } }
      }
    }'''
    graphql(reader,mutation,{'field':FIELD,'options':options})
    after,updated=read(reader)
    (backup/'after.json').write_text(json.dumps(after,indent=2),encoding='utf-8')
    if updated['options'][:len(field['options'])]!=field['options']:
        raise RuntimeError('Existing Status options changed; inspect backup '+str(backup))
    if set(REQUIRED)-{o['name'] for o in updated['options']}:
        raise RuntimeError('Required options were not saved')
    comparison=json.loads(json.dumps(after))
    next(f for f in comparison['fields']['nodes'] if f.get('id')==FIELD)['options']=field['options']
    if comparison!=before:raise RuntimeError('Unrelated project values changed; inspect backup '+str(backup))
    return backup


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true',required=True)
    parser.add_argument('--recovery',type=Path,required=True)
    args=parser.parse_args()
    backup=configure(args.recovery)
    print('PASS: Project #4 Status options configured; existing field, option IDs and item values preserved.')
    print('Backup:',backup or 'Already configured; no changes')
