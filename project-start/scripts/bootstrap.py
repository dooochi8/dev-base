#!/usr/bin/env python3
"""Copy reviewed dev-base assets locally. Dry-run by default; no network or Git writes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT_FILES = ("AGENTS.md", "CLAUDE.md", ".gitignore", ".linear.example.json")
DOCS = ("linear.md", "project-setup.md", "workflows.md", "skill-sources.md")
SKIP = {".git", ".agents", ".claude", "__pycache__", ".DS_Store", "node_modules",
        ".venv", "tmp", "dist", "coverage"}


class BootstrapError(Exception):
    pass


def safe_file(path):
    name = path.name.lower()
    if (name.startswith(".env") or name in {".linear.json", ".linear_token", ".mcp.json", ".npmrc", ".netrc"}
            or name.endswith((".pem", ".key", ".p12", ".pfx"))
            or any(word in name for word in ("credential", "secret", "token"))):
        raise BootstrapError(f"認証・個別設定の可能性があるファイルを拒否: {path.name}")


def inventory(source):
    source = Path(source).expanduser().resolve(strict=True)
    skills = sorted(p.name for p in source.iterdir()
                    if not p.name.startswith(".") and (p / "SKILL.md").is_file())
    if "dev-base" not in skills or not (source / "scripts/sync-skills.sh").is_file():
        raise BootstrapError("dev-base構成ではありません")
    if not skills or any(not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) for name in skills):
        raise BootstrapError("スキル名が不正です")
    selected = []

    def walk(path):
        if path.name in SKIP or path.suffix == ".pyc":
            return
        if path.is_symlink():
            raise BootstrapError(f"正本内のsymlinkを拒否: {path.relative_to(source)}")
        safe_file(path)
        if path.is_dir():
            for child in sorted(path.iterdir()):
                walk(child)
        elif path.is_file():
            selected.append(path.relative_to(source))
        else:
            raise BootstrapError(f"通常ファイルではありません: {path.relative_to(source)}")

    optional = [name for name in ("LICENSE", "LICENSE.md", "NOTICE") if (source / name).exists()]
    for relative in [*ROOT_FILES, *optional, *(f"docs/{name}" for name in DOCS),
                     "scripts", "templates", ".github", *skills]:
        walk(source / relative)
    # Reject symlink ancestors too (e.g. docs pointing to an unrelated checkout).
    for relative in selected:
        if any((source / part).is_symlink() for part in [relative, *relative.parents] if part != Path(".")):
            raise BootstrapError("コピー対象の親にsymlinkがあります")
    return source, skills, sorted(set(selected))


def source_git(source):
    def run(*args):
        result = subprocess.run(["git", "-C", str(source), *args], capture_output=True, text=True, timeout=10)
        if result.returncode:
            raise BootstrapError("ベースのGit状態を確認できません")
        return result.stdout.strip()
    if Path(run("rev-parse", "--show-toplevel")).resolve() != source:
        raise BootstrapError("ベースにはGitルートを指定してください")
    return {"head": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain", "--untracked-files=all"))}


def bootstrap(source, destination, name, description, apply=False, allow_dirty=False):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", name) or name.endswith(".git"):
        raise BootstrapError("nameは英小文字・数字で始まるslugにしてください")
    if not description.strip():
        raise BootstrapError("目的の説明が必要です")
    source, skills, selected = inventory(source)
    requested = Path(destination).expanduser().absolute()
    if requested.exists() or requested.is_symlink():
        raise BootstrapError("出力先は既に存在します。上書きせず再開手順を確認してください")
    parent = requested.parent.resolve(strict=True)
    destination = parent / requested.name
    if destination == source or source in destination.parents:
        raise BootstrapError("ベースの内部へは作成できません")
    # No nested Git repositories, even when the new directory does not exist yet.
    if any((ancestor / ".git").exists() for ancestor in [parent, *parent.parents]):
        raise BootstrapError("既存Gitリポジトリの中へは作成できません")
    provenance = source_git(source)
    hashes = {str(p): hashlib.sha256((source / p).read_bytes()).hexdigest() for p in selected}
    plan = {"name": name, "destination": str(destination), "skills": skills,
            "source": provenance, "files": [str(p) for p in selected], "applied": False}
    if not apply:
        return plan
    if provenance["dirty"] and not allow_dirty:
        raise BootstrapError("未コミット内容があります。差分確認後だけ --allow-dirty-source を使ってください")
    destination.mkdir()  # exclusive; never replace an existing directory
    # If interrupted, preserve the partial directory for inspection; no automatic deletion.
    for relative in selected:
        origin = source / relative
        if origin.is_symlink() or hashlib.sha256(origin.read_bytes()).hexdigest() != hashes[str(relative)]:
            raise BootstrapError("計画後にコピー元が変わりました。部分出力を保持して停止します")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
    for skill in skills:
        codex = destination / ".agents/skills" / skill
        codex.parent.mkdir(parents=True, exist_ok=True)
        codex.symlink_to(f"../../{skill}", target_is_directory=True)
        shutil.copytree(destination / skill, destination / ".claude/skills" / skill,
                        ignore=lambda _directory, names: [n for n in names if n == "agents"])
    readme = (f"# {name}\n\n{description.strip()}\n\n"
              "## 開発の入口\n\n"
              "開発管理はLinear、コードとレビューはGitHub、仕様はdocsを正本とします。\n"
              "GitHub・Linearは未接続です。接続確認後にURLとIssue IDを追記してください。\n"
              "アプリの技術スタック・実装・実行コマンドは未定です。\n\n"
              "[開発ルール](AGENTS.md) / [初期設定](docs/project-setup.md) / "
              "[Linear](docs/linear.md) / [組み合わせ](docs/workflows.md)\n\n"
              "## 共通スキル\n\n" + "\n".join(f"- [`{s}`]({s}/SKILL.md)" for s in skills) +
              "\n\n## 共通検査\n\n```sh\nbash scripts/sync-skills.sh --check\n"
              "python3 -B -m unittest discover -s scripts -p 'test_*.py'\n```\n")
    (destination / "README.md").write_text(readme)
    agents = destination / "AGENTS.md"
    agents.write_text(agents.read_text().replace("# dev-base (Codex 向け規約)", f"# {name} 開発ルール", 1)
                      .replace("複製して新しい開発を始めるための共通ベース。", "dev-baseを基にした新規プロジェクト。", 1))
    manifest = {"schemaVersion": 1, "name": name, "template": "dev-base", "source": provenance,
                "skills": skills, "sourceFileHashes": hashes, "externalSetup": "not-run"}
    (destination / "docs/bootstrap.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    plan["applied"] = True
    return plan


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source", required=True)
    cli.add_argument("--dest", required=True)
    cli.add_argument("--name", required=True)
    cli.add_argument("--description", required=True)
    cli.add_argument("--apply", action="store_true")
    cli.add_argument("--allow-dirty-source", action="store_true")
    args = cli.parse_args()
    try:
        result = bootstrap(args.source, args.dest, args.name, args.description, args.apply, args.allow_dirty_source)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (BootstrapError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
