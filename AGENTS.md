# dev-base (Codex 向け規約)

複製して新しい開発を始めるための共通ベース。Codex / Claude Code の共通ルールの正本。このリポジトリでは `.agents/skills/` と `.claude/skills/` から同名のスキルを利用できる。初回設定は `docs/project-setup.md` を読む。

## 構造ルール

- スキルの単一ソースはトップレベルの `<skill>/SKILL.md`。編集は必ずここで行う。
- `.claude/skills/` は `./scripts/sync-skills.sh` による生成物。手で編集しない。
- `.agents/skills/` は同スクリプトが管理する正本へのリンク。リンクを実ディレクトリに置き換えない。
- スキルを編集したら `./scripts/sync-skills.sh` を実行する。
- 同期後は `./scripts/sync-skills.sh --check` で両方の入口を検証する。

## 実行時の必須ルール

1. 実行指示書（plan-handoff 形式）がある場合、その「触らないもの・禁止事項」を厳守する。指示書に無いリファクタ・依存追加・抽象化をしない。
2. 完了報告の前に必ず `verify` の姿勢で検証する。テスト・型チェック・lint を実際に実行し、出力を根拠として報告する。実行していないことを「確認済み」と言わない。
3. テストが落ちたとき、テスト自体を弱めて通さない。
4. 作業は薄い縦切りで進める。最初に tracer bullet を通す。

## 保守と役割

- 開始した環境で実装・検証を完了できる。計画者・実行者のモデルや引継ぎは固定しない。独立レビューや実際の引継ぎが必要な時だけ対応するスキルを使う。
- 本文は日本語とし、実際の起動判断に役立つdescriptionを付ける。共通の境界・完了条件を入口に、長い条件別手順をreferencesへ置く。固定行数を満たすための水増しや分割をしない。
- `agents/openai.yaml` は必要なUI情報がある時に維持・追加し、Claudeへの生成では除外する。

## スキルの選び方

- 把握: orient / 要件: grill-me（一問ずつ）, grilling（独立質問をラウンドで）, write-a-prd / 分解: prd-to-issues / 受け渡し: plan-handoff
- 実装: dev-base, tdd / デバッグ: debug / 確認: verify, review-diff / 設計改善: improve-codebase-architecture
- 説明の図解: show-me / 指示の独立評価: empirical-prompt-tuning / 開発Issue: linear-workflow
- スキルの追加・コピー依頼を、そのスキルの実行依頼と混同しない。必要なものだけ選び、全スキルを毎回実行しない。

連鎖の具体例は `docs/workflows.md` を参照。

## Linear / Gitの開発運用

- 開発の目的・優先順位・状態・完了条件はLinear、コードとレビューはGit/GitHub、仕様・ADR・試験はこのリポジトリのdocsを正本にする。日常タスクは従来のNotion等に残す。
- 接続は `./scripts/linear` を使う。初回は `discover` と `init`、以後は `doctor` でTeam/Projectを確認する。複製元の設定を新規プロジェクトへ持ち込まない。
- 実装・修正の前に同じ成果のIssueを確認し、なければ機能・成果単位で起票する。単なる手順を細切れにしない。同時進行数の固定上限は設けない。
- 説明・相談・読み取りだけの確認では自動起票しない。着手・レビュー待ち・完了状態は実際の進捗に合わせる。
- IssueはAPI・CLI・スクリプト・MCP等の自動化経由で削除しない。取りやめ・重複は理由と参照先を残してCanceled/Duplicateへ移す。完全削除はユーザー本人がLinear UIで行う。
- 更新前に対象IDと所属、更新後に同じID・内容・状態を確認する。未取得をゼロ、未実行を成功にしない。再試行前に現在値と重複を確認する。
- 認証情報をGit・Issue・ログへ保存しない。 `.linear.json` はTokenを含めず、複製対象から除外する。
- 通常の開発は `codex/<Issue-ID>-<内容>` のブランチとPRで行い、コミットとPRにIssue IDを含める。PRマージだけでIssueをDoneにしない。
- GitHub Issuesへ開発タスクを二重起票しない。既存のGitHub設定を変える時は対象リポジトリと依頼範囲を確認する。

操作・状態・失敗時の扱いは `docs/linear.md`、Issue本文は `templates/linear-issue.md` を参照する。
