# dev-base

日本語で使える開発用スキル集です。Codex 向けのスキルフォルダと、Claude Code 向けの `.claude/skills` を同じリポジトリ内で管理しています。

## 含まれるスキル

- `dev-base`: 日常的な実装、バグ修正、リファクタの共通ベース
- `grill-me`: 設計や方針を一問ずつ厳しく詰める
- `write-a-prd`: 実装前の PRD を整理して書く
- `prd-to-issues`: PRD を薄い縦切りの issue に分解する
- `tdd`: red-green-refactor で実装を進める
- `improve-codebase-architecture`: 設計上の摩擦を見つけて改善案を整理する

## ディレクトリ構成

- `dev-base/`, `grill-me/`, `write-a-prd/`, `prd-to-issues/`, `tdd/`, `improve-codebase-architecture/`
  Codex 向けのスキルフォルダ。各フォルダに `SKILL.md` があり、必要に応じて `agents/openai.yaml` を含みます。
- `.claude/skills/`
  Claude Code 向けのスキル配置。各スキルは同名ディレクトリ配下にあります。

## 使い方

### Claude Code

このリポジトリを開いた状態で、次のようにスラッシュコマンドで呼び出せます。

- `/dev-base`
- `/grill-me`
- `/write-a-prd`
- `/prd-to-issues`
- `/tdd`
- `/improve-codebase-architecture`

### Codex

Codex では Claude Code のような `/skill-name` 前提ではなく、プロンプトの中でスキル名を明示して使う想定です。

例:

- `dev-base を使ってこの修正を進めて`
- `grill-me でこの設計案を詰めて`
- `tdd でこのバグを直して`

## メモ

- すべてのスキル本文は日本語化しています。
- Claude Code 用と Codex 用で、呼び出し名はできるだけ揃えています。
