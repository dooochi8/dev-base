# dev-base

開発用スキル集のハーネスリポジトリ。日常開発の土台として、別プロジェクトからスキルを参照・コピーして使う。

## リポジトリの構造ルール

- **単一ソースはトップレベルの `<skill>/` フォルダ**。スキルの編集は必ずここで行う。
- `.claude/skills/` は `./scripts/sync-skills.sh` による**生成物**。手で編集しない。
- スキルを編集・追加・削除したら、必ず `./scripts/sync-skills.sh` を実行して同期する。
- 新しいスキルは `<name>/SKILL.md`（必須）と `<name>/agents/openai.yaml`（Codex 向け、必須）を持つ。

## モデル分業の前提

このリポジトリのスキルは「計画と実行の分業」を前提に設計されている。

- **計画・レビュー**（高性能モデル）: grill-me / write-a-prd / prd-to-issues / plan-handoff / review-diff
- **実行**（軽量モデル）: dev-base / tdd / debug / verify
- 実行者は plan-handoff 形式の実行指示書を受け取り、完了前に必ず verify の姿勢で検証する。

## スキルの選び方

- 未知のリポジトリを把握する → `orient`
- 要件・設計が曖昧 → `grill-me`
- 中規模以上の実装前 → `write-a-prd` → `prd-to-issues` → `plan-handoff`
- 日常的な実装・修正・リファクタ → `dev-base`
- 振る舞いをテストで定義できる実装 → `tdd`
- バグの原因が分からない → `debug`
- 完了前の検証 → `verify`
- 差分のレビュー → `review-diff`
- コードベース全体の設計改善 → `improve-codebase-architecture`

連鎖の具体例は `docs/workflows.md` を参照。

## スキルを書くときの規約

- 本文は日本語。語彙はリポジトリ全体で統一する: 縦切り / tracer bullet / deep module / 振る舞い / 観測可能。
- 節構成: frontmatter → ガードレール（前出し）→ 進め方 → 出力フォーマット → 完了条件。
- 1スキル 60〜120 行を目安にし、詳細な手順は `references/` に逃がす。
- description は「〜したいときに使う」が含まれる、起動判断できる文にする。
