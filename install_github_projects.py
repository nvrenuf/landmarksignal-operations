"""Focused launcher payload update. No configuration, board, or service writes."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import uuid


def sha(data):
    return hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()


def plan(source, root):
    entries=json.loads((source/'github_projects_assets.json').read_text(encoding='utf-8'))
    changes=[]
    for entry in entries:
        target=root/entry['target'];origin=source/entry['source']
        if target.is_symlink() or any(p.is_symlink() for p in target.parents if p!=root.parent):
            raise RuntimeError('Linked installation target refused')
        new=origin.read_bytes().replace(b'\r\n',b'\n')
        if sha(new)!=entry['new_sha256']:raise RuntimeError('Source checksum differs: '+entry['source'])
        old=target.read_bytes() if target.exists() else None
        if old is not None and sha(old)==sha(new):continue
        if (sha(old) if old is not None else None)!=entry['old_sha256']:
            raise RuntimeError('Unrecognized installed payload: '+entry['target'])
        changes.append((target,old,new))
    return changes


def install(source,root):
    changes=plan(source,root)
    if not changes:return None
    backup=root/'landmarksignal-v1/recovery'/('github-projects-'+uuid.uuid4().hex)
    backup.mkdir(parents=True)
    paths=[]
    for i,(path,old,new) in enumerate(changes):
        if old is not None:(backup/f'{i}.before').write_bytes(old)
        paths.append({'path':str(path),'backup':f'{i}.before' if old is not None else None,
                      'installed_sha256':sha(new)})
    (backup/'paths.json').write_text(json.dumps(paths,indent=2),encoding='utf-8')
    changed=[]
    try:
        for path,old,new in changes:
            if (path.read_bytes() if path.exists() else None)!=old:raise RuntimeError('Payload changed during install')
            # In-place writes preserve the original Windows owner and ACL.
            # Record before writing so even a partial write is rolled back.
            changed.append((path,old))
            with path.open('wb' if old is not None else 'xb') as stream:
                stream.write(new);stream.flush();os.fsync(stream.fileno())
        if any(path.read_bytes()!=new for path,old,new in changes):raise RuntimeError('Installed bytes differ')
    except BaseException:
        for path,old in reversed(changed):
            if old is None:
                if path.exists():path.unlink()
            elif path.read_bytes()!=old:path.write_bytes(old)
        raise
    return backup


def main():
    if os.name!='nt':raise RuntimeError('Native Windows installation only')
    root=Path(os.environ['LOCALAPPDATA'])/'hermes'
    sys.path.insert(0,str(root/'hermes-agent'))
    import hermes_bootstrap
    # Managed runpy/bootstrap can replace sys.path; restore companions afterwards.
    source=Path(__file__).resolve().parent
    sys.path.insert(0,str(source))
    import subprocess
    from github_queue_intake import REVISION
    from execution_guard_v1_final import ExecutionGuard
    revision=subprocess.run(['git','-C',str(root/'hermes-agent'),'rev-parse','HEAD'],
                            check=True,capture_output=True,text=True).stdout.strip()
    if revision!=REVISION:raise RuntimeError('Hermes revision changed; compatibility review needed')
    def apply():
        board=root/'kanban/boards/landmarksignal/kanban.db'
        with closing(sqlite3.connect(board.resolve().as_uri()+'?mode=ro',uri=True)) as conn:
            if conn.execute("SELECT count(*) FROM tasks WHERE status='running'").fetchone()[0]:
                raise RuntimeError('Work is running; no installation')
        backup=install(source,root)
        print('PASS: launcher payload installed and verified; configuration and board untouched.')
        print('Backup:',backup or 'Already installed; no changes')
    ExecutionGuard('33','install-github-projects',timeout=0).execute(apply)


if __name__=='__main__':
    try:main()
    except PermissionError:
        print('Protected launcher payload requires scoped file maintenance.',file=sys.stderr)
        sys.exit(13)
