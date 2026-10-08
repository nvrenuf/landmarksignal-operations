"""Explicit native Kanban result return to GitHub Project #3 for human review."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from github_queue_intake import gh, digest

URL=re.compile(r'^https://github\.com/(nvrenuf/[A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)$')


def inspect_results(root):
    database=root/'kanban/boards/landmarksignal/kanban.db'
    work_root=(root/'landmarksignal-v1/work/github-intake').resolve()
    with closing(sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True)) as conn:
        conn.row_factory=sqlite3.Row
        if conn.execute("SELECT count(*) FROM tasks WHERE status='running'").fetchone()[0]:
            raise RuntimeError('Wait for running LandmarkSignal work before returning results')
        result=[]
        for row in conn.execute('SELECT * FROM tasks'):
            card=dict(row)
            if card['status'] not in ('review','done','blocked') or not card.get('workspace_path'): continue
            workspace=Path(card['workspace_path']).resolve()
            if not workspace.is_relative_to(work_root): continue
            source_path=workspace/'github-source.json'
            if not source_path.is_file(): continue
            source=json.loads(source_path.read_text(encoding='utf-8-sig'))
            issue=source['issue'];url=issue['url']
            if not URL.fullmatch(url) or source.get('project_owner')!='nvrenuf' or source.get('project_number')!=3: continue
            # Export the original intake root, not every decomposed prerequisite.
            if not (card.get('idempotency_key','') or '').startswith('github-project3:'): continue
            run=conn.execute('SELECT * FROM task_runs WHERE task_id=? ORDER BY id DESC LIMIT 1',(card['id'],)).fetchone()
            if run is None: continue
            artifacts=[]
            for file in sorted(workspace.iterdir()):
                if file.is_symlink() or not file.is_file() or file.suffix not in ('.py','.md'): continue
                artifacts.append({'name':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'size':file.stat().st_size})
            r={'task_id':card['id'],'title':card['title'],'status':card['status'],'issue_url':url,
               'project_id':source['project_id'],'project_item_id':source['project_item_id'],
               'board':'landmarksignal','workspace':str(workspace),'run':dict(run),'artifacts':artifacts,
               'proposed_status':'Blocked' if card['status']=='blocked' else 'Human Review',
               'acceptance_verified':False}
            r['snapshot_sha256']=digest(r);result.append(r)
        return result


def graphql(reader,query,variables):
    value=json.loads(reader(['api','graphql','--input','-'],{'query':query,'variables':variables}))
    if value.get('errors'): raise RuntimeError('GitHub Project operation failed')
    return value['data']


def return_result(root, task_id, snapshot_sha256, reader=gh):
    rows=[r for r in inspect_results(root) if r['task_id']==task_id]
    if len(rows)!=1 or rows[0]['snapshot_sha256']!=snapshot_sha256:
        raise RuntimeError('Result changed; refresh before returning it')
    record=rows[0]
    if reader(['api','user','--jq','.login']).strip()!='nvrenuf': raise RuntimeError('GitHub account must be nvrenuf')
    match=URL.fullmatch(record['issue_url']);repo,number=match.groups()
    live=json.loads(reader(['api',f'repos/{repo}/issues/{number}']))
    if live.get('state')!='open': raise RuntimeError('Issue is closed; review it in GitHub before returning results')
    query='''query($project:ID!,$item:ID!){project:node(id:$project){... on ProjectV2{id number owner{... on User{login}} fields(first:100){pageInfo{hasNextPage} nodes{... on ProjectV2SingleSelectField{id name options{id name}}}}}} item:node(id:$item){... on ProjectV2Item{project{id} content{... on Issue{url}}}}}'''
    data=graphql(reader,query,{'project':record['project_id'],'item':record['project_item_id']})
    project,item=data['project'],data['item']
    if (project['number']!=3 or project['owner'].get('login')!='nvrenuf'
        or item['project']['id']!=project['id'] or item['content']['url']!=record['issue_url']):
        raise RuntimeError('Project/item/issue binding differs')
    if project['fields']['pageInfo']['hasNextPage']: raise RuntimeError('Project fields truncated')
    fields=[f for f in project['fields']['nodes'] if f.get('name')=='Status']
    if len(fields)!=1: raise RuntimeError('Expected exactly one existing Status field')
    options=[o for o in fields[0]['options'] if o['name']==record['proposed_status']]
    if len(options)!=1: raise RuntimeError('Required existing review/block status unavailable')
    marker='<!-- landmarksignal-result:'+record['snapshot_sha256']+' -->'
    pages=json.loads(reader(['api',f'repos/{repo}/issues/{number}/comments','--paginate','--slurp']))
    comments=[c for page in pages for c in page]
    if not any(marker in c.get('body','') for c in comments):
        run=record['run']
        body=(marker+'\n## Hermes work returned for human review\n\n'
              'Acceptance has **not** been verified. Native Done is a worker report, not human acceptance.\n\n'
              f"Board: {record['board']}\nTask: {task_id}\nRun: {run['id']}\nProfile: {run.get('profile')}\n"
              f"Workspace: `{record['workspace']}`\nNative status: {record['status']}\nOutcome: {run.get('outcome')}\n\n"
              +str(run.get('summary') or 'No worker summary recorded')[:6000]+'\n\nArtifact inventory:\n'
              +'\n'.join('- '+a['name']+' — SHA256 '+a['sha256'] for a in record['artifacts']))
        reader(['api',f'repos/{repo}/issues/{number}/comments','--method','POST','--input','-'],{'body':body})
    mutation='''mutation($project:ID!,$item:ID!,$field:ID!,$option:String!){updateProjectV2ItemFieldValue(input:{projectId:$project,itemId:$item,fieldId:$field,value:{singleSelectOptionId:$option}}){projectV2Item{id}}}'''
    graphql(reader,mutation,{'project':project['id'],'item':record['project_item_id'],'field':fields[0]['id'],'option':options[0]['id']})
    verify='''query($item:ID!){node(id:$item){... on ProjectV2Item{fieldValueByName(name:"Status"){... on ProjectV2ItemFieldSingleSelectValue{name}}}}}'''
    current=graphql(reader,verify,{'item':record['project_item_id']})
    if current['node']['fieldValueByName']['name']!=record['proposed_status']: raise RuntimeError('Remote status verification failed')
    location=root/'landmarksignal-v1/returns';location.mkdir(parents=True,exist_ok=True)
    (location/(record['snapshot_sha256']+'.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
    return {'issue_url':record['issue_url'],'status':record['proposed_status'],'task_id':task_id,
            'acceptance_verified':False,'issue_closed':False}
