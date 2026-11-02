#!/usr/bin/env bash
# トップレベル正本をClaudeの生成物とCodexのリンクへ同期する。
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - "${1:-sync}" <<'PY'
from pathlib import Path
import filecmp
import os
import shutil
import sys

root = Path.cwd()
mode = sys.argv[1]
if mode not in {"sync", "--check"}:
    print("usage: sync-skills.sh [--check]", file=sys.stderr)
    sys.exit(2)
claude = root / ".claude/skills"
codex = root / ".agents/skills"
skills = sorted(p for p in root.iterdir() if not p.name.startswith(".") and (p / "SKILL.md").is_file())
if not skills:
    print("スキルが見つかりません", file=sys.stderr)
    sys.exit(1)
ignored = {"node_modules", "__pycache__", ".venv", ".DS_Store"}


def excluded(package, directory, names):
    return [name for name in names if name in ignored or name.endswith((".pyc", ".pyo"))
            or (name == "agents" and Path(directory) == package)]


def entries(package):
    found = {}
    if not package.is_dir():
        return found
    for directory, dirs, files in os.walk(package, followlinks=False):
        dropped = set(excluded(package, directory, [*dirs, *files]))
        dirs[:] = [name for name in dirs if name not in dropped]
        for name in [*dirs, *(name for name in files if name not in dropped)]:
            path = Path(directory) / name
            kind = "link" if path.is_symlink() else "directory" if path.is_dir() else "file"
            found[path.relative_to(package)] = kind
    return found


def identical(source, target):
    left, right = entries(source), entries(target)
    if left != right:
        return False
    for relative, kind in left.items():
        a, b = source / relative, target / relative
        if kind == "file" and not filecmp.cmp(a, b, shallow=False):
            return False
        if kind == "link" and os.readlink(a) != os.readlink(b):
            return False
    return True


names = {p.name for p in skills}
if mode == "--check":
    problems = []
    for source in skills:
        if not identical(source, claude / source.name):
            problems.append(f"drift: {source.name}")
        link = codex / source.name
        if not link.is_symlink() or os.readlink(link) != f"../../{source.name}" or not (link / "SKILL.md").is_file():
            problems.append(f"drift: .agents/skills/{source.name}")
    for folder in (claude, codex):
        if folder.is_dir():
            problems.extend(f"orphan: {path.relative_to(root)}" for path in folder.iterdir() if path.name not in names)
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("OK: drift なし")
    sys.exit(0)

claude.mkdir(parents=True, exist_ok=True)
codex.mkdir(parents=True, exist_ok=True)
for path in codex.iterdir():
    if not path.is_symlink():
        print(f"conflict: {path.relative_to(root)} は管理対象のリンクではありません", file=sys.stderr)
        sys.exit(1)
for folder in (claude, codex):
    for path in folder.iterdir():
        if path.name not in names:
            if path.is_symlink() or path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
            print(f"removed: {path.relative_to(root)}")
for source in skills:
    target = claude / source.name
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, symlinks=True, ignore=lambda directory, names: excluded(source, directory, names))
    link = codex / source.name
    if link.is_symlink():
        link.unlink()
    link.symlink_to(f"../../{source.name}", target_is_directory=True)
    print(f"synced: {source.name}")
print(f"完了: {len(skills)} スキルを .claude/skills と .agents/skills へ同期しました")
PY
