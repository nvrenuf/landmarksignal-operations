"""Apply conservative Jeeves settings while preserving existing config bytes.

This configures limits only. It does not install an execution guard, dispatch a
task, authorize a child, or authenticate a human approval.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime, timezone
import uuid

import yaml

HERMES_REVISION = "b1968795b2569d2f7a2fc541328399c952679c25"
POLICY = {
    "kanban": {
        "dispatch_in_gateway": False,
        "max_in_progress": 1,
        "max_in_progress_per_profile": 1,
        "max_spawn": 1,
        "failure_limit": 1,
    },
    "delegation": {
        "max_concurrent_children": 1,
        "max_spawn_depth": 1,
        "child_timeout_seconds": 300,
    },
    "agent": {"max_turns": 20},
    "approvals": {
        "mode": "manual",
        "cron_mode": "deny",
        "unattended_mode": "deny",
        "timeout": 120,
    },
}


def prepare(original):
    """Append new sections or recognize an already-applied policy; never rewrite.

    Existing conflicting/partial sections require review, so they fail closed.
    Unknown keys elsewhere and their exact bytes, comments and line endings stay.
    """
    old = yaml.safe_load(original.decode("utf-8-sig"))
    if not isinstance(old, dict):
        raise ValueError("Expected an existing YAML mapping")
    present = set(POLICY).intersection(old)
    if present:
        if present == set(POLICY) and all(
            isinstance(old[section], dict)
            and all(type(old[section].get(key)) is type(value)
                    and old[section].get(key) == value
                    for key, value in values.items())
            for section, values in POLICY.items()
        ):
            return original
        raise ValueError("Policy sections already exist and need review: "
                         + ", ".join(sorted(present)))
    newline = b"\r\n" if b"\r\n" in original else b"\n"
    addition = yaml.safe_dump(POLICY, sort_keys=False).encode("utf-8")
    addition = addition.replace(b"\n", newline)
    updated = original + newline + b"# LandmarkSignal V1 conservative execution limits" + newline + addition
    parsed = yaml.safe_load(updated.decode("utf-8-sig"))
    if {key: value for key, value in parsed.items() if key not in POLICY} != old:
        raise ValueError("Existing configuration would change")
    for section, expected in POLICY.items():
        if parsed.get(section) != expected:
            raise ValueError("Policy verification failed")
    return updated


def apply_configuration(path):
    path = Path(path)
    original = path.read_bytes()
    updated = prepare(original)
    if updated == original:
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name("config.pre-v1-" + stamp + "-" + uuid.uuid4().hex[:8] + ".yaml")
    with backup.open("xb") as stream:
        stream.write(original)
        stream.flush()
        os.fsync(stream.fileno())
    fd, temporary = tempfile.mkstemp(prefix=".config-v1-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        if path.read_bytes() != original:
            raise RuntimeError("Configuration changed during preparation; no replacement made")
        os.replace(temporary, path)
        if path.read_bytes() != updated:
            raise RuntimeError("Post-write verification failed; backup retained at " + str(backup))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Installation requires native Windows Python")
    root = Path(os.environ["LOCALAPPDATA"]) / "hermes"
    runtime = root / "hermes-agent"
    revision = subprocess.run(
        ["git", "-C", str(runtime), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if revision != HERMES_REVISION:
        raise RuntimeError("Installed Hermes revision changed; review compatibility before applying")
    config = root / "profiles" / "jeeves" / "config.yaml"
    original = config.read_bytes()
    updated = prepare(original)
    print("Profile config:", config)
    print("Hermes revision:", revision)
    print("Original SHA256:", hashlib.sha256(original).hexdigest())
    if args.apply:
        backup = apply_configuration(config)
        print("Backup:", backup if backup else "Already configured; no write needed")
    else:
        print("PREVIEW ONLY; use --apply to save")
    print(json.dumps(POLICY, indent=2))
    if args.apply:
        # Verify how the installed Hermes loader merges these exact settings.
        os.environ["HERMES_HOME"] = str(config.parent)
        os.environ["HERMES_PROFILE"] = "jeeves"
        import sys
        sys.path.insert(0, str(runtime))
        from hermes_cli.config import load_config
        effective = load_config()
        for section, values in POLICY.items():
            for key, expected in values.items():
                actual = effective.get(section, {}).get(key)
                if type(actual) is not type(expected) or actual != expected:
                    raise RuntimeError("Installed loader disagrees on " + section + "." + key)
        print("PASS: installed Hermes loader reads all configured limits")
        print("Existing model/session/terminal/memory settings preserved")
        print("Reload Jeeves's Hermes runtime before relying on startup settings")
        print("No task claimed or dispatched; no child approved")
        print("Live guard integration and exact issue/task binding remain pending")


if __name__ == "__main__":
    main()
