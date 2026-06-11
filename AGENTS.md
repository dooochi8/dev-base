# dev-base (Codex 向け規約)

開発用スキル集のハーネスリポジトリ。Codex からは、プロンプト内でスキル名を明示して使う（例: 「dev-base を使ってこの修正を進めて」）。

## 構造ルール

- スキルの単一ソースはトップレベルの `<skill>/SKILL.md`。編集は必ずここで行う。
- `.claude/skills/` は `./scripts/sync-skills.sh` による生成物。手で編集しない。
- スキルを編集したら `./scripts/sync-skills.sh` を実行する。

## 実行時の必須ルール

1. 実行指示書（plan-handoff 形式）がある場合、その「触らないもの・禁止事項」を厳守する。指示書に無いリファクタ・依存追加・抽象化をしない。
2. 完了報告の前に必ず `verify` の姿勢で検証する。テスト・型チェック・lint を実際に実行し、出力を根拠として報告する。実行していないことを「確認済み」と言わない。
3. テストが落ちたとき、テスト自体を弱めて通さない。
4. 作業は薄い縦切りで進める。最初に tracer bullet を通す。

## スキルの選び方

- 把握: orient / 要件: grill-me, write-a-prd / 分解: prd-to-issues / 受け渡し: plan-handoff
- 実装: dev-base, tdd / デバッグ: debug / 確認: verify, review-diff / 設計改善: improve-codebase-architecture

連鎖の具体例は `docs/workflows.md` を参照。
