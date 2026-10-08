import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import install_operations_skill as update


class SkillUpdateTests(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory)
        source, target, recovery = root / "source", root / "target", root / "recovery"
        original, replacement, hashes = {}, {}, {}
        for name in update.FILES:
            original[name] = ("old inspected " + name + "\r\n").encode()
            replacement[name] = ("new reviewed " + name + "\n").encode()
            dst = target / name
            src = source / "skills" / "landmarksignal-operations" / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(original[name])
            src.write_bytes(replacement[name])
            hashes[name] = update.hashlib.sha256(replacement[name]).hexdigest()
        (target / "retained.txt").write_bytes(b"preserve unrelated skill resource")
        (source / "operations_skill_update_manifest.json").write_text(json.dumps({
            "inspected_old_normalized_sha256": {k: update.normalized(v) for k, v in original.items()},
            "new_sha256": hashes,
        }))
        return source, target, recovery, original, replacement

    def test_backup_preservation_and_idempotence(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            source, target, recovery, old, new = self.fixture(directory)
            backup = update.install(source, target, recovery)
            for name in update.FILES:
                self.assertEqual((backup / "skill-before" / name).read_bytes(), old[name])
                self.assertEqual((target / name).read_bytes(), new[name])
            self.assertEqual((target / "retained.txt").read_bytes(), b"preserve unrelated skill resource")
            self.assertIsNone(update.install(source, target, recovery))
            self.assertEqual(len(list(recovery.iterdir())), 1)

    def test_recognized_previous_revision_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            source, target, recovery, old, new = self.fixture(directory)
            path = source / "operations_skill_update_manifest.json"
            manifest = json.loads(path.read_text())
            previous = b"recognized later installed revision\n"
            (target / "SKILL.md").write_bytes(previous)
            manifest["accepted_previous_normalized_sha256"] = {
                k: [v] for k, v in manifest["inspected_old_normalized_sha256"].items()
            }
            manifest["accepted_previous_normalized_sha256"]["SKILL.md"].append(update.normalized(previous))
            path.write_text(json.dumps(manifest))
            backup = update.install(source, target, recovery)
            self.assertEqual((backup / "skill-before" / "SKILL.md").read_bytes(), previous)
            self.assertEqual((target / "SKILL.md").read_bytes(), new["SKILL.md"])

    def test_declared_payload_and_reviewed_observed_revision(self):
        source = Path(__file__).resolve().parent
        manifest = json.loads((source / "operations_skill_update_manifest.json").read_text())
        for name in update.FILES:
            payload = (source / "skills" / "landmarksignal-operations" / name).read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(update.hashlib.sha256(payload).hexdigest(), manifest["new_sha256"][name])
        self.assertIn("0db8857aa77dbe9ef15ebc72eb65473a8b6a44efc40045cd808f27a175cff5d9", manifest["accepted_previous_normalized_sha256"]["SKILL.md"])

    def test_unknown_local_edit_stops_before_any_update(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target, recovery, old, new = self.fixture(directory)
            (target / "SKILL.md").write_bytes(b"unexpected local edit")
            before = {p: p.read_bytes() for p in target.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(RuntimeError, "differs from the inspected snapshot"):
                update.install(source, target, recovery)
            self.assertEqual({p: p.read_bytes() for p in before}, before)
            self.assertFalse(recovery.exists())

    def test_windows_crlf_checkout_installs_canonical_payload(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            source, target, recovery, old, new = self.fixture(directory)
            for name in update.FILES:
                (source / "skills" / "landmarksignal-operations" / name).write_bytes(
                    new[name].replace(b"\n", b"\r\n")
                )
            backup = update.install(source, target, recovery)
            for name in update.FILES:
                self.assertEqual((target / name).read_bytes(), new[name])
                self.assertEqual((backup / "skill-before" / name).read_bytes(), old[name])
            self.assertIsNone(update.install(source, target, recovery))

    def test_failed_second_replace_rolls_back_first(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target, recovery, old, new = self.fixture(directory)
            real_replace = update.os.replace
            count = 0
            def fail_once(src, dst):
                nonlocal count
                count += 1
                if count == 2:
                    raise PermissionError("simulated Windows permission failure")
                return real_replace(src, dst)
            with patch.object(update.os, "replace", side_effect=fail_once):
                with self.assertRaises(PermissionError):
                    update.install(source, target, recovery)
            for name in update.FILES:
                self.assertEqual((target / name).read_bytes(), old[name])
            self.assertEqual(len(list(recovery.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
