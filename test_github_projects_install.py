from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
import install_github_projects as installer
from configure_project4_status import prepare_options, REQUIRED


class InstallTests(unittest.TestCase):
    def test_backup_repeat_unknown_edit_and_write_failure_rollback(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source';source.mkdir();target=root/'target';target.mkdir()
            manifest=[]
            for name,old in (('one.py',b'old\r\n'),('two.py',None)):
                (source/name).write_bytes(b'new\n')
                if old is not None:(target/name).write_bytes(old)
                manifest.append({'source':name,'target':name,'old_sha256':installer.sha(old) if old else None,'new_sha256':installer.sha(b'new\n')})
            (source/'github_projects_assets.json').write_text(json.dumps(manifest))
            real=Path.open
            def fail(path,*args,**kwargs):
                if path==target/'two.py' and args and args[0]=='xb':raise PermissionError('Simulated write failure')
                return real(path,*args,**kwargs)
            with patch.object(Path,'open',fail),self.assertRaises(PermissionError):installer.install(source,target)
            self.assertEqual((target/'one.py').read_bytes(),b'old\r\n')
            self.assertFalse((target/'two.py').exists())
            backup=installer.install(source,target)
            self.assertEqual((backup/'0.before').read_bytes(),b'old\r\n')
            self.assertEqual(len(json.loads((backup/'paths.json').read_text())),2)
            self.assertIsNone(installer.install(source,target))
            (target/'one.py').write_bytes(b'unknown edit')
            with self.assertRaises(RuntimeError):installer.install(source,target)

    def test_status_options_preserve_ids_and_are_idempotent(self):
        old=[{'id':'TODO','name':'Todo','color':'GREEN','description':'keep'}]
        result=prepare_options(old)
        self.assertEqual(result[0],old[0])
        self.assertEqual({r['name'] for r in result[1:]},set(REQUIRED))
        self.assertEqual(prepare_options(result),result)

    def test_manifest_matches_source(self):
        root=Path(__file__).resolve().parent
        entries=json.loads((root/'github_projects_assets.json').read_text())
        self.assertEqual(len(entries),6)
        for e in entries:self.assertEqual(installer.sha((root/e['source']).read_bytes()),e['new_sha256'])
