"""Back up and reconcile only the five inspected Jeeves Operations skill files."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import uuid

FILES = {
    "SKILL.md", "references/hermes-kanban.md",
    "references/hermes-kanban-safety.md", "references/execution-guard-v1.md",
    "references/acceptance-test.md",
}


def normalized(data):
    return hashlib.sha256(data.decode("utf-8-sig").replace("\r\n", "\n").strip().encode()).hexdigest()


def install(source, target, recovery):
    source, target, recovery = Path(source), Path(target), Path(recovery)
    manifest = json.loads((source / "operations_skill_update_manifest.json").read_text())
    old = manifest["inspected_old_normalized_sha256"]
    new = manifest["new_sha256"]
    if set(old) != FILES or set(new) != FILES:
        raise RuntimeError("Update manifest differs from the reviewed five-file scope")
    payload = source / "skills" / "landmarksignal-operations"
    replacements, originals = {}, {}
    for relative in sorted(FILES):
        src, dst = payload / relative, target / relative
        if src.is_symlink() or dst.is_symlink():
            raise RuntimeError("Refusing a linked skill file: " + relative)
        # Git may check Markdown out as CRLF on Windows. Verify/install the
        # canonical LF payload; accept no other content normalization.
        content = src.read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(content).hexdigest() != new[relative]:
            raise RuntimeError("Source checksum differs: " + relative)
        current = dst.read_bytes()
        if current == content:
            continue
        if normalized(current) != old[relative]:
            raise RuntimeError("Installed skill differs from the inspected snapshot: " + relative)
        replacements[relative], originals[relative] = content, current
    if not replacements:
        print("PASS: Operations skill is already reconciled; no changes.")
        return None
    backup = recovery / ("operations-skill-" + uuid.uuid4().hex)
    shutil.copytree(target, backup / "skill-before", symlinks=True)
    # Recheck after the backup; never overwrite an intervening edit.
    for relative, content in originals.items():
        if (target / relative).read_bytes() != content:
            raise RuntimeError("Skill changed during backup; no update performed")
    changed = []
    try:
        for relative, content in replacements.items():
            dst = target / relative
            temporary = dst.with_name(dst.name + "." + uuid.uuid4().hex + ".tmp")
            try:
                temporary.write_bytes(content)
                os.replace(temporary, dst)
                changed.append(relative)
            finally:
                temporary.unlink(missing_ok=True)
        for relative in FILES:
            if hashlib.sha256((target / relative).read_bytes()).hexdigest() != new[relative]:
                raise RuntimeError("Installed-file verification failed: " + relative)
    except Exception:
        for relative in reversed(changed):
            dst = target / relative
            temporary = dst.with_name(dst.name + ".rollback-" + uuid.uuid4().hex)
            temporary.write_bytes(originals[relative])
            os.replace(temporary, dst)
        raise
    (backup / "update.json").write_text(json.dumps({
        "updated_files": sorted(replacements), "new_sha256": new,
        "configuration_changed": False, "task_records_changed": False,
        "generation_or_dispatch_performed": False,
    }, indent=2) + "\n")
    print("PASS: Five-file Operations skill reconciliation installed and verified.")
    print("Full skill backup:", backup / "skill-before")
    print("Generic GitHub skills, configuration, board and evidence untouched.")
    print("No model call, card creation, dispatch, authorization or infrastructure change.")
    print("Start a fresh Jeeves conversation to avoid old skill text in chat context.")
    print("Reusable guarded GitHub intake/specification is NOT installed by this update.")
    return backup


def main():
    if os.name != "nt" or not os.environ.get("LOCALAPPDATA"):
        raise RuntimeError("Install this update using Lee's native Windows Python")
    if len(sys.argv) != 1:
        raise RuntimeError("Installer accepts no alternate profile or target arguments")
    root = Path(os.environ["LOCALAPPDATA"]) / "hermes"
    target = root / "profiles" / "jeeves" / "skills" / "software-development" / "landmarksignal-operations"
    if target.is_symlink():
        raise RuntimeError("Refusing a linked Operations skill directory")
    install(Path(__file__).resolve().parent, target,
            root / "landmarksignal-v1" / "recovery")


if __name__ == "__main__":
    main()
