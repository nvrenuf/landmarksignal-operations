"""Verify preservation, fail-closed edits and repeatability of profile setup."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from configure_jeeves_v1 import POLICY, apply_configuration, prepare


class ConfigurationTests(unittest.TestCase):
    def test_existing_settings_and_crlf_are_preserved_byte_for_byte(self):
        original = (b"# keep this comment\r\nmodel:\r\n  default: current-model\r\n"
                    b"  provider: local\r\nterminal:\r\n  timeout: 73\r\n")
        updated = prepare(original)
        self.assertTrue(updated.startswith(original))
        self.assertNotIn(b"\n", updated.replace(b"\r\n", b""))

    def test_conflicting_partial_sections_are_not_overwritten(self):
        for original in (b"model: {}\nkanban:\n  max_in_progress: 4\n",
                         b"model: {}\napprovals:\n  deny: [keep-me]\n"):
            with self.assertRaises(ValueError):
                prepare(original)

    def test_apply_backs_up_original_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            original = b"model:\n  default: keep-this-model\n"
            path.write_bytes(original)
            backup = apply_configuration(path)
            self.assertEqual(backup.read_bytes(), original)
            applied = path.read_bytes()
            self.assertIsNone(apply_configuration(path))
            self.assertEqual(path.read_bytes(), applied)
            self.assertEqual(len(list(path.parent.glob("config.pre-v1-*.yaml"))), 1)

    def test_failed_replace_leaves_original_and_backup_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            original = b"model: {}\n"
            path.write_bytes(original)
            with patch("configure_jeeves_v1.os.replace", side_effect=PermissionError("locked")):
                with self.assertRaises(PermissionError):
                    apply_configuration(path)
            self.assertEqual(path.read_bytes(), original)
            backups = list(path.parent.glob("config.pre-v1-*.yaml"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), original)
            self.assertEqual(list(path.parent.glob(".config-v1-*")), [])

    def test_invalid_config_and_wrong_boolean_types_fail_closed(self):
        for original in (b"[]\n", b"model: [broken\n"):
            with self.assertRaises(Exception):
                prepare(original)
        import yaml
        config = {"model": {}, **POLICY}
        config["kanban"] = {**POLICY["kanban"], "dispatch_in_gateway": 0}
        with self.assertRaises(ValueError):
            prepare(yaml.safe_dump(config).encode())


if __name__ == "__main__":
    unittest.main(verbosity=2)
