# dev-base

日本語で使える開発用スキル集です。Codex 向けのスキルフォルダと、Claude Code 向けの `.claude/skills` を同じリポジトリ内で管理しています。

## 含まれるスキル

ライフサイクル順（把握→要件→分解→受け渡し→実装→確認→設計改善）に並べています。

| スキル | 役割 |
|--------|------|
| `orient` | 未知のリポジトリを最短で把握し、以降の作業の土台になるマップを作る |
| `grill-me` | 設計案・要件・方針を一問ずつ厳しく詰め、未解決の前提をなくす |
| `write-a-prd` | 実装前に PRD を整理して書く |
| `prd-to-issues` | PRD を薄い縦切りの issue 群に分解する |
| `plan-handoff` | 計画者が実行者へ渡す実行指示書を作る |
| `dev-base` | 日常的な実装・バグ修正・リファクタの共通ベース |
| `tdd` | red-green-refactor で振る舞い中心に実装を進める |
| `debug` | 系統的に原因を特定して直す（再現→最小化→仮説→切り分け） |
| `verify` | 変更後に実際に動かし、出力を根拠に完了を判断する |
| `review-diff` | 差分をレビューし、バグと単純化の観点で指摘する |
| `improve-codebase-architecture` | 設計上の摩擦を見つけて改善案を整理する |

## モデル分業の前提

このリポジトリのスキルは「計画と実行の分業」を前提に設計されています。

- **計画・レビュー**（高性能モデル）: `orient` / `grill-me` / `write-a-prd` / `prd-to-issues` / `plan-handoff` / `review-diff`
- **実行**（軽量モデル）: `dev-base` / `tdd` / `debug` / `verify`

スキルの連鎖パターン（小さな修正・バグ修正・中規模以上の機能開発）の詳細は `docs/workflows.md` を参照してください。

## ディレクトリ構成

- `orient/`, `grill-me/`, `write-a-prd/`, `prd-to-issues/`, `plan-handoff/`, `dev-base/`, `tdd/`, `debug/`, `verify/`, `review-diff/`, `improve-codebase-architecture/`
  **単一ソース**。スキルの編集は必ずトップレベルの各フォルダで行います。各フォルダに `SKILL.md` があり、必要に応じて `agents/openai.yaml` を含みます。
- `.claude/skills/`
  Claude Code 向けのスキル配置。`./scripts/sync-skills.sh` による**生成物**であり、手で編集しません。

## 使い方

### スキルを編集・追加・削除したとき

トップレベルのスキルフォルダを編集した後、必ず sync スクリプトを実行して `.claude/skills/` へ反映します。

```sh
./scripts/sync-skills.sh
```

`.claude/skills/` を直接編集した内容はスクリプト実行時に上書きされます。

### Claude Code

このリポジトリを開いた状態で、スラッシュコマンドで呼び出せます。

- `/orient`
- `/grill-me`
- `/write-a-prd`
- `/prd-to-issues`
- `/plan-handoff`
- `/dev-base`
- `/tdd`
- `/debug`
- `/verify`
- `/review-diff`
- `/improve-codebase-architecture`

### Codex

プロンプトの中でスキル名を明示して使います。

例:

- `dev-base を使ってこの修正を進めて`
- `grill-me でこの設計案を詰めて`
- `plan-handoff で実行指示書を作って`
- `verify で完了前に確認して`

## メモ

- すべてのスキル本文は日本語です。
- Claude Code 用と Codex 用で、呼び出し名はできるだけ揃えています。
- リポジトリ全体の設計方針は `CLAUDE.md` と `docs/harness-plan.md` を参照してください。
