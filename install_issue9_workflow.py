"""Install the focused Issue 9 corrections without releasing or rewriting cards."""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import uuid


def sha(data): return hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()


def prepare_config(original, root_profile=False):
    import yaml
    text=original.decode('utf-8-sig').replace('\r\n','\n'); before=yaml.safe_load(text)
    if not isinstance(before,dict): raise ValueError('Expected configuration mapping')
    settings={'kanban':{'review_dispatch':False,'max_in_progress':1,'max_in_progress_per_profile':1,'max_spawn':1}}
    if root_profile:
        plugins=dict(before.get('plugins') or {})
        if 'landmarksignal-execution' in plugins.get('disabled',[]):
            raise ValueError('Execution plugin explicitly disabled; not overriding it')
        enabled=list(plugins.get('enabled') or [])
        if 'landmarksignal-execution' not in enabled: enabled.append('landmarksignal-execution')
        plugins['enabled']=enabled;settings['plugins']=plugins
    for section, values in settings.items():
        merged=dict(before.get(section) or {});merged.update(values)
        addition=yaml.safe_dump({section:merged},sort_keys=False).rstrip('\n')+'\n'
        pattern=re.compile(r'^'+re.escape(section)+r':[^\n]*\n(?:(?:[ \t]+[^\n]*|[ \t]*|#[^\n]*)\n)*',re.MULTILINE)
        matches=list(pattern.finditer(text))
        if len(matches)>1: raise ValueError('Duplicate section: '+section)
        if section in before and not matches: raise ValueError('Unsupported inline section: '+section)
        if matches:
            m=matches[0];text=text[:m.start()]+addition+text[m.end():]
        else: text=text.rstrip('\r\n')+'\n'+addition
    after=yaml.safe_load(text)
    expected=dict(before)
    for section,values in settings.items(): expected[section]={**(before.get(section) or {}),**values}
    if after!=expected: raise ValueError('Unrelated configuration would change')
    newline='\r\n' if b'\r\n' in original else '\n'
    return text.replace('\r\n','\n').replace('\n',newline).encode('utf-8')


def replace(path,value):
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        with temporary.open('xb') as stream:
            stream.write(value);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()


def apply_changes(changes, originals, recovery):
    backup=recovery/('issue9-workflow-'+uuid.uuid4().hex)
    backup.mkdir(parents=True)
    for i,(target,old) in enumerate(originals.items()):
        if old is not None:(backup/(str(i)+'.before')).write_bytes(old)
    (backup/'paths.json').write_text(json.dumps([{'path':str(p),'backup':str(i)+'.before' if b is not None else None} for i,(p,b) in enumerate(originals.items())],indent=2))
    changed=[]
    try:
        for path,value in changes.items():
            if (path.read_bytes() if path.exists() else None)!=originals[path]:raise RuntimeError('File changed during installation')
            replace(path,value);changed.append(path)
        if any(p.read_bytes()!=v for p,v in changes.items()):raise RuntimeError('Installed bytes differ')
    except BaseException:
        for path in reversed(changed):
            if originals[path] is None:path.unlink()
            else:replace(path,originals[path])
        raise
    return backup


def main():
    if os.name!='nt': raise RuntimeError('Native Windows installation only')
    root=Path(os.environ['LOCALAPPDATA'])/'hermes';runtime=root/'hermes-agent'
    sys.path.insert(0,str(runtime))
    import hermes_bootstrap
    source=Path(__file__).resolve().parent;sys.path.insert(0,str(source))
    import subprocess
    revision=subprocess.run(['git','-C',str(runtime),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
    if revision!='0c2ff854a5c5121c75ac0b0a35241a580ee27fb7': raise RuntimeError('Hermes revision changed; no installation')
    board=root/'kanban/boards/landmarksignal/kanban.db'
    connection=sqlite3.connect(board.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        connection.execute('PRAGMA query_only=ON')
        if connection.execute("SELECT count(*) FROM tasks WHERE status='running'").fetchone()[0]:
            raise RuntimeError('A task is running; no installation')
    finally:connection.close()
    from github_queue_intake import read_queue
    read_queue()  # Validate the fresh Project query and nvrenuf account before writes.
    manifest=json.loads((source/'issue9_workflow_assets.json').read_text())
    changes={};originals={}
    for entry in manifest:
        target=root/entry['target'];new=(source/entry['source']).read_bytes().replace(b'\r\n',b'\n')
        if sha(new)!=entry['new_sha256']: raise RuntimeError('Source checksum differs: '+entry['source'])
        if target.is_symlink(): raise RuntimeError('Linked target: '+str(target))
        old=target.read_bytes() if target.exists() else None
        if old is not None and sha(old)==sha(new): continue
        if old is None and entry['old_sha256'] is not None: raise RuntimeError('Expected installed file missing: '+str(target))
        if old is not None and sha(old) not in entry['allowed_old_sha256']: raise RuntimeError('Unrecognized local change: '+str(target))
        changes[target]=new;originals[target]=old
    for path,default in ((root/'config.yaml',True),(root/'profiles/jeeves/config.yaml',False)):
        old=path.read_bytes();new=prepare_config(old,default)
        if new!=old:changes[path]=new;originals[path]=old
    backup=apply_changes(changes,originals,root/'landmarksignal-v1/recovery')
    print('PASS: recognized corrections installed; native cards and run history unchanged')
    print('PASS: configured review_dispatch=false for default and Jeeves; concurrency=1')
    print('PASS: worker completion requires Review; ordinary project tools remain available')
    print('Backup:',backup)
    print('No task release/retry, model call, GitHub write, issue close or merge performed')

if __name__=='__main__':main()
