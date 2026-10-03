#!/usr/bin/env python3
"""Verify pinned pstack source files, local references and skill entry points."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def check(root):
    root = Path(root).resolve()
    manifest = json.loads((root / "docs/pstack-manifest.json").read_text())
    problems = []
    paths = set()
    if not re.fullmatch(r"[a-f0-9]{40}", manifest.get("commit", "")):
        problems.append("manifest: 固定commitが不正")
    for record in [*manifest["files"], *manifest.get("licenseFiles", [])]:
        relative = Path(record["path"])
        path = root / relative
        if relative.is_absolute() or ".." in relative.parts or root not in path.resolve().parents:
            problems.append(f"manifest: 範囲外のpath {relative}")
            continue
        if relative.as_posix() in paths:
            problems.append(f"manifest: pathが重複 {relative}")
        paths.add(relative.as_posix())
        if not path.is_file() or path.is_symlink():
            problems.append(f"missing: {relative}")
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            problems.append(f"source drift: {relative}")
        for client in (".agents/skills", ".claude/skills"):
            if relative.parts[0] == "docs" or not (root / client).is_dir():
                continue
            projected = root / client / relative
            if not projected.is_file() or hashlib.sha256(projected.read_bytes()).hexdigest() != record["sha256"]:
                problems.append(f"projection drift: {client}/{relative}")
    for name in manifest["skills"]:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            problems.append(f"manifest: スキル名が不正 {name}")
            continue
        package = root / name
        entry = package / "SKILL.md"
        if not entry.is_file():
            problems.append(f"missing entry: {name}")
            continue
        text = entry.read_text()
        front = re.match(r"---\n(.*?)\n---\n", text, re.S)
        if not front or not re.search(r"^name: " + re.escape(name) + r"$", front[1], re.M):
            problems.append(f"frontmatter: {name}")
        if not front or not re.search(r"^description: \S.+$", front[1], re.M):
            problems.append(f"description: {name}")
        for required in ("UPSTREAM-SKILL.md", "UPSTREAM.md", "LICENSE-pstack", "LICENSE-cursor-team-kit"):
            if not (package / required).is_file():
                problems.append(f"missing: {name}/{required}")
        for document in package.rglob("*.md"):
            if any(part in {"node_modules", "__pycache__", ".venv"} for part in document.relative_to(package).parts):
                continue
            for match in LINK.finditer(document.read_text()):
                target = match[1].split("#", 1)[0]
                if not target or "://" in target or target.startswith(("mailto:", "<")):
                    continue
                destination = (document.parent / target).resolve()
                if not destination.exists():
                    problems.append(f"broken link: {document.relative_to(root)} -> {target}")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        problems = check(args.root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    manifest = json.loads((args.root / "docs/pstack-manifest.json").read_text())
    print(f"OK: pstack {manifest['version']}, {len(manifest['skills'])} skills, {len(manifest['files'])} pinned files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
