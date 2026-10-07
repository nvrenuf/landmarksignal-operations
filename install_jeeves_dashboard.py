"""Install dashboard launch assets only; never dispatch a task or restart a process."""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
if __name__ == "__main__":
    root = Path(os.environ["LOCALAPPDATA"]) / "hermes"
    os.environ["HERMES_HOME"] = str(root / "profiles/jeeves")
    os.environ["HERMES_PROFILE"] = "jeeves"
    sys.path.insert(0, str(root / "hermes-agent"))
    import hermes_bootstrap  # noqa: F401

import yaml

NAME = "landmarksignal-launch"


def enable_plugin(original):
    """Preserve every config byte outside the value being edited."""
    text = original.decode("utf-8-sig")
    raw = yaml.safe_load(text) or {}
    if not isinstance(raw, dict):
        raise RuntimeError("Configuration must be a mapping")
    plugins = raw.get("plugins", {})
    if not isinstance(plugins, dict) or not isinstance(plugins.get("enabled", []), list) or not isinstance(plugins.get("disabled", []), list):
        raise RuntimeError("Existing plugins settings require review")
    if NAME in plugins.get("disabled", []):
        raise RuntimeError("Launch plugin is explicitly disabled; no override made")
    if NAME in plugins.get("enabled", []):
        return original
    expected = {**raw, "plugins": {**plugins, "enabled": [*plugins.get("enabled", []), NAME]}}
    newline = "\r\n" if "\r\n" in text else "\n"
    root = yaml.compose(text)
    plugin_node = next((v for k, v in root.value if k.value == "plugins"), None) if root else None
    if plugin_node is None:
        updated = text + ("" if text.endswith("\n") else newline) + yaml.safe_dump({"plugins": expected["plugins"]}, sort_keys=False).replace("\n", newline)
    else:
        enabled_node = next((v for k, v in plugin_node.value if k.value == "enabled"), None)
        node = enabled_node or plugin_node
        replacement = yaml.safe_dump(expected["plugins"]["enabled"] if enabled_node else expected["plugins"],
                                     default_flow_style=True, sort_keys=False, width=1000000).strip()
        if node.end_mark.line != node.start_mark.line:
            replacement += newline + " " * node.end_mark.column
        updated = text[:node.start_mark.index] + replacement + text[node.end_mark.index:]
    if yaml.safe_load(updated) != expected:
        raise RuntimeError("Plugin enable could not preserve configuration values")
    bom = b"\xef\xbb\xbf" if original.startswith(b"\xef\xbb\xbf") else b""
    return bom + updated.encode("utf-8")


def main():
    from install_jeeves_policy import bootstrap, verify_installed
    root, runtime, profile = bootstrap()
    verify_installed(profile)
    source = Path(__file__).resolve().parent
    target = root / "plugins" / NAME
    files = {}
    for path in (source / "plugins" / NAME).rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            files[str(path.relative_to(source / "plugins" / NAME))] = path.read_bytes()
    for name in ("guarded_issue7_document.py", "execution_guard_v1_final.py", "install_jeeves_policy.py",
                 "landmarksignal_policy.py", "configure_jeeves_v1.py"):
        files[str(Path("dashboard/runner") / name)] = (source / name).read_bytes()
    for name in ("__init__.py", "plugin.yaml"):
        files[str(Path("dashboard/runner/plugins/landmarksignal-execution") / name)] = (source / "plugins/landmarksignal-execution" / name).read_bytes()
    configs = [root / "config.yaml", profile / "config.yaml"]
    changes = []
    for config in configs:
        if not config.is_file():
            raise RuntimeError("Expected existing configuration is missing: " + str(config))
        before = config.read_bytes()
        changes.append((config, before, enable_plugin(before)))
    if target.exists():
        if any(not (target / name).is_file() or (target / name).read_bytes() != value for name, value in files.items()):
            raise RuntimeError("Existing dashboard plugin differs; no files overwritten")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".jeeves-dashboard-", dir=target.parent))
        try:
            for name, value in files.items():
                path = temporary / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(value)
            temporary.rename(target)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    for config, before, after in changes:
        if before != after:
            if config.read_bytes() != before:
                raise RuntimeError("Configuration changed during install; stop for review")
            backup = config.with_name("config.pre-dashboard-" + tag + ".yaml")
            backup.write_bytes(before)
            temporary = config.with_name(".config-dashboard-" + tag + ".tmp")
            temporary.write_bytes(after)
            os.replace(temporary, config)
            print("Config backup:", backup)
    for name, value in files.items():
        if (target / name).read_bytes() != value:
            raise RuntimeError("Installed asset differs: " + name)
    print("PASS: dashboard plugin and pinned worker assets installed")
    print("Existing model, policy and execution limits preserved")
    print("No task started; existing card and workspace untouched")
    print("Restart only the browser dashboard to mount the new backend routes")
    print("Then open http://127.0.0.1:9119/kanban?profile=jeeves")


if __name__ == "__main__":
    main()
