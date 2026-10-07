"""Install only the batch-Triage intake control in the existing dashboard plugin."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid


def sha(data):
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def install(source, target, recovery):
    manifest = json.loads((source / 'github_intake_assets.json').read_text(encoding='utf-8-sig'))
    payload = {
        'dashboard/plugin_api.py': source / 'plugins/landmarksignal-launch/dashboard/plugin_api.py',
        'dashboard/dist/index.js': source / 'plugins/landmarksignal-launch/dashboard/dist/index.js',
        'dashboard/runner/github_queue_intake.py': source / 'github_queue_intake.py',
    }
    old = manifest['old_sha256']
    data = {name: path.read_bytes().replace(b'\r\n', b'\n') for name, path in payload.items()}
    if {name: sha(value) for name, value in data.items()} != manifest['new_sha256']:
        raise RuntimeError('Reviewed intake payload checksum differs')
    before = {}
    for name, content in data.items():
        path = target / name
        if path.is_symlink():
            raise RuntimeError('Unexpected linked launcher asset: ' + name)
        current = path.read_bytes() if path.exists() else None
        before[name] = current
        expected_old = old.get(name)
        if current is not None and sha(current) == sha(content):
            continue
        if current is None and expected_old is None:
            continue
        if current is None or sha(current) != expected_old:
            raise RuntimeError('Installed launcher differs from reviewed old/new assets: ' + name)
    if all(before[name] is not None and sha(before[name]) == sha(value) for name, value in data.items()):
        return None
    backup = recovery / ('github-intake-' + uuid.uuid4().hex)
    shutil.copytree(target, backup / 'plugin-before', symlinks=True)
    changed = []
    try:
        for name, value in data.items():
            path = target / name
            current = path.read_bytes() if path.exists() else None
            if current != before[name]:
                raise RuntimeError('Launcher changed during installation')
            if current is not None and sha(current) == sha(value):
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
            try:
                temporary.write_bytes(value)
                os.replace(temporary, path)
            finally:
                if temporary.exists(): temporary.unlink()
            changed.append(name)
        if any(sha((target / name).read_bytes()) != sha(value) for name, value in data.items()):
            raise RuntimeError('Installed payload verification failed')
    except BaseException:
        for name in reversed(changed):
            path = target / name
            if before[name] is None:
                path.unlink()
            else:
                temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.rollback')
                try:
                    temporary.write_bytes(before[name])
                    os.replace(temporary, path)
                finally:
                    if temporary.exists(): temporary.unlink()
        raise
    (backup / 'installation.json').write_text(json.dumps({'installed_at': datetime.now(timezone.utc).isoformat(),
        'new_sha256': manifest['new_sha256'], 'configuration_changed': False,
        'cards_created': 0, 'model_calls': 0, 'tasks_dispatched': 0}, indent=2), encoding='utf-8')
    return backup


def main():
    if os.name != 'nt' or len(sys.argv) != 1:
        raise RuntimeError('Run this installer with native Windows Python and no arguments')
    root = Path(os.environ['LOCALAPPDATA']) / 'hermes'
    runtime = root / 'hermes-agent'
    profile = root / 'profiles/jeeves'
    os.environ['HERMES_HOME'] = str(profile)
    os.environ['HERMES_PROFILE'] = 'jeeves'
    sys.path.insert(0, str(runtime))
    import hermes_bootstrap  # dependency activation before native imports
    from github_queue_intake import REVISION, read_queue
    from execution_guard_v1_final import ExecutionGuard, HAS_WIN32EVENT
    if not HAS_WIN32EVENT:
        raise RuntimeError('Native mutex support unavailable; nothing installed')
    revision = subprocess.run(['git', '-C', str(runtime), 'rev-parse', 'HEAD'], check=True,
                              capture_output=True, text=True).stdout.strip()
    if revision != REVISION:
        raise RuntimeError('Installed Hermes revision needs compatibility review; nothing installed')
    changed_native = subprocess.run(['git', '-C', str(runtime), 'status', '--porcelain', '--',
        'hermes_cli/kanban_db.py', 'hermes_cli/kanban_db_connect.py'], check=True,
        capture_output=True, text=True).stdout.strip()
    if changed_native:
        raise RuntimeError('Native Kanban files have local changes; nothing installed')
    target = root / 'plugins/landmarksignal-launch'
    if not target.is_dir() or target.is_symlink():
        raise RuntimeError('Existing launcher directory missing or linked')
    board = root / 'kanban/boards/landmarksignal/kanban.db'
    if not board.is_file():
        raise RuntimeError('Existing LandmarkSignal board missing')
    configs = [root / 'config.yaml', profile / 'config.yaml']
    before_config = {path: path.read_bytes() for path in configs}
    import yaml
    for path in configs:
        config = yaml.safe_load(before_config[path]) or {}
        plugins = config.get('plugins') or {}
        if 'landmarksignal-launch' not in plugins.get('enabled', []) or 'landmarksignal-launch' in plugins.get('disabled', []):
            raise RuntimeError('Existing launcher plugin is not enabled')
    settings = yaml.safe_load(before_config[profile / 'config.yaml'])
    if (settings.get('kanban', {}).get('dispatch_in_gateway') is not False
            or settings.get('kanban', {}).get('review_dispatch') is not False):
        raise RuntimeError('Existing Jeeves automatic dispatch limits differ; no settings changed')
    source = Path(__file__).resolve().parent
    guard_source = (source / 'execution_guard_v1_final.py').read_bytes()
    installed_guard = target / 'dashboard/runner/execution_guard_v1_final.py'
    if not installed_guard.is_file() or sha(installed_guard.read_bytes()) != sha(guard_source):
        raise RuntimeError('Installed launcher guard differs; no guard replacement performed')
    # Fresh signed-in account, project, queue and dependency read preflight. No import.
    from hermes_cli import kanban_db as kb
    import inspect
    required = {'triage', 'initial_status', 'assignee', 'workspace_kind', 'workspace_path', 'project_id', 'board', 'idempotency_key', 'max_retries'}
    if not required.issubset(inspect.signature(kb.create_task).parameters):
        raise RuntimeError('Native create_task interface differs; nothing installed')
    import sqlite3
    from contextlib import closing
    with closing(sqlite3.connect(board.resolve().as_uri() + '?mode=ro', uri=True)) as conn:
        if conn.execute("SELECT count(*) FROM tasks WHERE status='running'").fetchone()[0]:
            raise RuntimeError('A task is running; no installation or restart performed')
    queue = read_queue()
    print('PASS: nvrenuf Project #3 queue read verified; queued issues:', len(queue))
    def apply():
        backup = install(source, target, root / 'landmarksignal-v1/recovery')
        if any(path.read_bytes() != original for path, original in before_config.items()):
            raise RuntimeError('Configuration changed concurrently; return the report')
        print('PASS: batch GitHub-to-Triage button installed and verified')
        print('Backup:', backup or 'Already installed; no file changes')
        print('No card imported, model called, specification run, task dispatched or configuration changed')
        print('Import queued work appears in the existing Jeeves Launch tab')
        print('This imports to Triage only. Existing specification/Ready/execution controls are unchanged.')
    ExecutionGuard('9', 'install-github-intake', timeout=0).execute(apply)


if __name__ == '__main__':
    main()
