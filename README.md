# dev-base

新しい開発で複製して使う、日本語の開発ベースです。共通ルール、22本のスキル、Linear用コマンドとIssueテンプレートを同梱しています。Codexの既定はGPT-6 Astraです。アプリの技術スタックやLinearのProjectは複製先で設定します。

[ECC](https://github.com/affaan-m/ECC)の調査・セキュリティ・検証・作業再開の手法を、既存のスキルへ統合しています。[採用範囲と出典](docs/ecc-adoption.md) / [GPT-6 Astraの設定と使い方](docs/codex.md)を参照してください。

一式まとめて始める場合は [`project-start`](project-start/SKILL.md) に「新しいプロジェクト名と目的」を渡してください。ローカル複製、GitHub、Linear、初期Issueと検証を扱い、未確定の外部作成先だけ確認します。

まず [新しいプロジェクトの始め方](docs/project-setup.md) を読み、`./scripts/sync-skills.sh --check` と `./scripts/linear --help` で入口を確認してください。Linear操作にはPython 3.9以降とAPIキーが必要です。個人のVaultへの参照や追加Pythonパッケージは不要です。

## 含まれるスキル

ライフサイクル順（把握→要件→分解→受け渡し→実装→確認→設計改善）に並べています。

| スキル | 役割 |
|--------|------|
| `project-start` | 開発ベース・GitHub・Linear・スキル一式を揃えて新規プロジェクトを始める |
| `orient` | 未知のリポジトリを最短で把握し、以降の作業の土台になるマップを作る |
| `search-first` | 新しい依存・連携・共通機能の導入前に、既存実装と候補を比較する |
| `grill-me` | 設計案・要件・方針を一問ずつ厳しく詰め、未解決の前提をなくす |
| `grilling` | 独立した質問をラウンドにまとめ、前提・依存・失敗条件を詰める |
| `write-a-prd` | 実装前に PRD を整理して書く |
| `plan-eng-review` | 要件・実装計画の技術設計、データ構造、エラー処理、範囲をレビューする |
| `plan-design-review` | 画面・導線の計画や、空・エラー・読み込み中の状態をレビューする |
| `prd-to-issues` | PRD を薄い縦切りの issue 群に分解する |
| `plan-handoff` | 計画者が実行者へ渡す実行指示書を作る |
| `dev-base` | 日常的な実装・バグ修正・リファクタの共通ベース |
| `tdd` | red-green-refactor で振る舞い中心に実装を進める |
| `debug` | 系統的に原因を特定して直す（再現→最小化→仮説→切り分け） |
| `verify` | 変更後に実際に動かし、出力を根拠に完了を判断する |
| `review-diff` | 差分をレビューし、バグと単純化の観点で指摘する |
| `security-review` | 認証・認可・外部入力・秘密情報・決済の変更を信頼境界から確認する |
| `improve-codebase-architecture` | 設計上の摩擦を見つけて改善案を整理する |
| `show-me` | 処理・構造・設計案を図や小さなHTMLで説明する |
| `smart-docs` | コードを根拠に日本語の設計文書・開発ガイド・構成図を作成する |
| `emil-design-eng` | Emil Kowalskiの原則に基づき、UIの細部・アニメーション・操作感を磨く |
| `empirical-prompt-tuning` | 指示・Skillを独立実行で評価し、固定要件に基づいて改善する |
| `linear-workflow` | Linearの接続・Issue・実装結果を管理する |

要件と計画のレビューから実装・テスト・デバッグ・UIの仕上げ・文書化まで、作業に合うスキルを選べます。特定のクラウドやフレームワークのスキルは、複製先の技術選定後に必要なものを追加します。導入元と移植内容は [Skill sources](docs/skill-sources.md) を参照してください。

`emil-design-eng` は [emilkowalski/skills](https://github.com/emilkowalski/skills) の中心スキルを収録しています。日本語の入口と上流原文・MITライセンスを同梱し、原文の詳細なコード例を参照できます。Swift/Expo向け等の別スキルは含みません。

## Linear

プロジェクトごとの接続情報はGit管理外の `.linear.json` に保存し、APIキーは `LINEAR_API_KEY` またはユーザー領域の `.linear_token` から読みます。

```sh
./scripts/linear discover
./scripts/linear init --team-id TEAM_UUID --project-id PROJECT_UUID
./scripts/linear doctor
./scripts/linear list
```

一覧・詳細・作成・更新・コメント・取消に対応します。削除コマンドはありません。詳細は [Linear運用](docs/linear.md)、本文例は [Issueテンプレート](templates/linear-issue.md) を参照してください。

## GPT-6 Astraを中心に進める

`.codex/config.toml` は `gpt-6-astra` / `xhigh` を既定にします。アプリやCLIで明示したモデル選択、利用可否、信頼・管理設定については [設定ガイド](docs/codex.md) を確認してください。

計画・実装・検証を同じ環境で完了できます。実際に担当を分ける場合だけ `plan-handoff` を使い、独立したレビューが必要な場合だけ追加の担当を使います。

スキルの連鎖パターン（小さな修正・バグ修正・中規模以上の機能開発）の詳細は `docs/workflows.md` を参照してください。

## ディレクトリ構成

- `orient/`, `grill-me/`, `write-a-prd/`, `prd-to-issues/`, `plan-handoff/`, `dev-base/`, `tdd/`, `debug/`, `verify/`, `review-diff/`, `improve-codebase-architecture/`
  **単一ソース**。スキルの編集は必ずトップレベルの各フォルダで行います。各フォルダに `SKILL.md` があり、必要に応じて `agents/openai.yaml` を含みます。
- `.claude/skills/`
  Claude Code 向けのスキル配置。`./scripts/sync-skills.sh` による**生成物**であり、手で編集しません。
- `.agents/skills/`
  Codex が発見するトップレベル正本への相対リンク。同じスクリプトで管理します。
- `.codex/config.toml`
  プロジェクトのモデル・推論設定。グローバル設定や権限、MCP、hooksは同梱しません。

## 使い方

### スキルを編集・追加・削除したとき

トップレベルのスキルフォルダを編集した後、必ず sync スクリプトを実行して `.claude/skills/` へ反映します。

```sh
./scripts/sync-skills.sh
./scripts/sync-skills.sh --check
```

`.claude/skills/` を直接編集した内容はスクリプト実行時に上書きされます。

### Claude Code

このリポジトリを開いた状態で、スラッシュコマンドで呼び出せます。

- `/orient`
- `/search-first`
- `/security-review`
- `/project-start`
- `/grill-me`
- `/grilling`
- `/write-a-prd`
- `/plan-eng-review`
- `/plan-design-review`
- `/prd-to-issues`
- `/plan-handoff`
- `/dev-base`
- `/tdd`
- `/debug`
- `/verify`
- `/review-diff`
- `/improve-codebase-architecture`
- `/show-me`
- `/smart-docs`
- `/emil-design-eng`
- `/empirical-prompt-tuning`
- `/linear-workflow`

### Codex

このリポジトリを開くと `.agents/skills/` から発見できます。`$dev-base` 等で明示して使えます。他のアプリのリポジトリには自動でグローバル配布しません。

例:

- `dev-base を使ってこの修正を進めて`
- `grill-me でこの設計案を詰めて`
- `plan-eng-review でこの実装計画の技術的な抜けを確認して`
- `plan-design-review でこの画面仕様の導線と例外状態を確認して`
- `plan-handoff で実行指示書を作って`
- `verify で完了前に確認して`
- `smart-docs でこのリポジトリの構成と主要フローをdocsにまとめて`
- `emil-design-eng でこの画面の見た目と操作感を磨いて`

## メモ

- すべてのスキルの入口は日本語です。上流の原文を保持する参照資料には英語を含みます。
- Claude Code 用と Codex 用で、呼び出し名はできるだけ揃えています。
- 現在の設計方針は `AGENTS.md` と `docs/codex.md` を参照してください。`docs/harness-plan.md` は初期設計の履歴です。
