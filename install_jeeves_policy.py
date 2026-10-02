"""Install the reviewed execution policy in the existing Jeeves profile only."""

from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

import yaml

from configure_jeeves_v1 import HERMES_REVISION, POLICY

PLUGIN_NAME = "landmarksignal-execution"


def disable_review_dispatch(original):
    raw = yaml.safe_load(original)
    existing = raw.get("kanban", {}).get("review_dispatch")
    if existing is False:
        return original
    if "review_dispatch" in raw.get("kanban", {}):
        raise RuntimeError("An explicit review_dispatch setting needs review before changing")
    node = yaml.compose(original.decode("utf-8-sig"))
    value = next(value for key, value in node.value if key.value == "kanban")
    lines = original.splitlines(keepends=True)
    newline = b"\r\n" if b"\r\n" in original else b"\n"
    # Insert at the next root node, retaining all existing config bytes.
    position = value.end_mark.line
    if position and position <= len(lines) and not lines[position - 1].endswith(b"\n"):
        lines[position - 1] += newline
    lines.insert(position, b"  review_dispatch: false" + newline)
    updated = b"".join(lines)
    expected = {**raw, "kanban": {**raw["kanban"], "review_dispatch": False}}
    if yaml.safe_load(updated) != expected:
        raise RuntimeError("Human-review setting could not be added safely")
    return updated


def bootstrap():
    if os.name != "nt":
        raise RuntimeError("Native Windows Python is required")
    root = Path(os.environ["LOCALAPPDATA"]) / "hermes"
    runtime = root / "hermes-agent"
    profile = root / "profiles" / "jeeves"
    revision = subprocess.run(["git", "-C", str(runtime), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
    if revision != HERMES_REVISION:
        raise RuntimeError("Hermes revision changed; compatibility review required")
    raw = yaml.safe_load((profile / "config.yaml").read_bytes())
    for section, keys in POLICY.items():
        for key, value in keys.items():
            if raw.get(section, {}).get(key) != value:
                raise RuntimeError("Missing conservative setting: " + section + "." + key)
    for flag in ("HERMES_YOLO_MODE", "HERMES_ENABLE_PROJECT_PLUGINS"):
        if os.environ.get(flag, "").lower() not in {"", "0", "false", "no", "off"}:
            raise RuntimeError("Remove the process override before proceeding: " + flag)
    os.environ["HERMES_HOME"] = str(profile)
    os.environ["HERMES_PROFILE"] = "jeeves"
    os.environ["HERMES_KANBAN_HOME"] = str(root)
    os.environ["HERMES_KANBAN_BOARD"] = "landmarksignal"
    os.environ["HERMES_KANBAN_DB"] = str(root / "kanban/boards/landmarksignal/kanban.db")
    # This process never owns a dispatcher-spawned worker or its inherited route.
    for name in ("HERMES_KANBAN_TASK", "HERMES_KANBAN_CLAIM_LOCK", "HERMES_KANBAN_RUN_ID",
                 "HERMES_KANBAN_WORKSPACE", "HERMES_INFERENCE_MODEL", "HERMES_INFERENCE_PROVIDER"):
        if os.environ.get(name):
            raise RuntimeError("Run from Lee's PowerShell, outside an agent/worker context: " + name)
    sys.path.insert(0, str(runtime))
    from dotenv import load_dotenv
    load_dotenv(profile / ".env", override=True)
    # A profile .env may not opt this reviewed entry back into bypass mode.
    if os.environ.get("HERMES_YOLO_MODE", "").lower() not in {"", "0", "false", "no", "off"}:
        raise RuntimeError("Jeeves profile enables approval bypass; review it before proceeding")
    if (os.environ.get("HERMES_HOME") != str(profile)
            or os.environ.get("HERMES_PROFILE") != "jeeves"
            or os.environ.get("HERMES_KANBAN_HOME") != str(root)
            or os.environ.get("HERMES_KANBAN_BOARD") != "landmarksignal"
            or os.environ.get("HERMES_KANBAN_DB") != str(root / "kanban/boards/landmarksignal/kanban.db")):
        raise RuntimeError("Profile environment changes the reviewed profile/board binding")
    for name in ("HERMES_KANBAN_TASK", "HERMES_KANBAN_CLAIM_LOCK", "HERMES_KANBAN_RUN_ID",
                 "HERMES_KANBAN_WORKSPACE", "HERMES_INFERENCE_MODEL", "HERMES_INFERENCE_PROVIDER"):
        if os.environ.get(name):
            raise RuntimeError("Profile environment supplies a worker context: " + name)
    return root, runtime, profile


def source_files():
    here = Path(__file__).resolve().parent
    plugin = here / "plugins" / PLUGIN_NAME
    return {
        "__init__.py": (plugin / "__init__.py").read_bytes(),
        "plugin.yaml": (plugin / "plugin.yaml").read_bytes(),
        "policy.py": (here / "landmarksignal_policy.py").read_bytes(),
    }


def verify_installed(profile):
    target = profile / "plugins" / PLUGIN_NAME
    for name, expected in source_files().items():
        if not (target / name).is_file() or (target / name).read_bytes() != expected:
            raise RuntimeError("Installed policy differs from reviewed code: " + name)
    from hermes_cli.plugins import discover_plugins, get_pre_tool_call_block_message
    discover_plugins()
    for tool in ("delegate_task", "write_file", "terminal", "kanban_create", "kanban_unblock"):
        message = get_pre_tool_call_block_message(tool, {"path": "test.txt"})
        if not isinstance(message, str) or not message.startswith("LANDMARKSIGNAL_V1: "):
            raise RuntimeError("Native Hermes policy gate did not block unowned " + tool)
    print("PASS: installed Hermes hook blocks unowned writes, shell, delegation and task mutations")


def install(profile):
    config = profile / "config.yaml"
    original = config.read_bytes()
    raw = yaml.safe_load(original)
    updated = disable_review_dispatch(original)
    if "plugins" in raw:
        enabled = raw["plugins"].get("enabled") if isinstance(raw["plugins"], dict) else None
        if not isinstance(enabled, list) or PLUGIN_NAME not in enabled:
            raise RuntimeError("Existing plugins configuration needs review; it was not overwritten")
        if PLUGIN_NAME in raw["plugins"].get("disabled", []):
            raise RuntimeError("Policy plugin is explicitly disabled")
    else:
        newline = b"\r\n" if b"\r\n" in original else b"\n"
        addition = yaml.safe_dump({"plugins": {"enabled": [PLUGIN_NAME]}}, sort_keys=False).encode()
        updated = updated + newline + addition.replace(b"\n", newline)
        parsed = yaml.safe_load(updated)
        expected = {**raw, "kanban": {**raw["kanban"], "review_dispatch": False}}
        if {key: value for key, value in parsed.items() if key != "plugins"} != expected:
            raise RuntimeError("Existing profile settings would change")
    target = profile / "plugins" / PLUGIN_NAME
    files = source_files()
    if target.exists():
        if any(not (target / name).is_file() or (target / name).read_bytes() != content
               for name, content in files.items()):
            raise RuntimeError("An existing policy directory differs; no overwrite performed")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".landmarksignal-install-", dir=target.parent))
        try:
            for name, content in files.items():
                (temporary / name).write_bytes(content)
            temporary.rename(target)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    if updated != original:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = config.with_name("config.pre-policy-" + stamp + "-" + uuid.uuid4().hex[:8] + ".yaml")
        with backup.open("xb") as stream:
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())
        fd, name = tempfile.mkstemp(prefix=".config-policy-", dir=config.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(updated)
                stream.flush()
                os.fsync(stream.fileno())
            if config.read_bytes() != original:
                raise RuntimeError("Configuration changed concurrently; plugin was not enabled")
            os.replace(name, config)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        print("Profile backup:", backup)
    verify_installed(profile)
    print("Installed policy:", target)
    print("Restart Jeeves's Hermes runtime to activate this policy in existing sessions")
    print("Read/planning tools remain available; execution uses the manual guarded entry")
    print("No task was claimed or dispatched, and no model was contacted")


if __name__ == "__main__":
    _, _, profile = bootstrap()
    install(profile)
