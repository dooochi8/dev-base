# dev-base ハーネス設計プラン

このリポジトリを「今後のすべての開発の土台となるハーネス」に育てるための設計と実行計画。

## 中心思想：計画と実行の分業

実運用は次のモデル分業を前提とする。

- **計画・レビュー**: 高性能モデル（Opus / Fable など）。要件を詰め、実行指示書を書き、最後に差分をレビューする。
- **実行**: 軽量モデル（Sonnet / Haiku など）。実行指示書に従って実装し、必ず検証してから完了を報告する。

この分業を成立させるため、ハーネスは次の3点を構造で強制する。

1. **再解釈不要な実行指示書**（`plan-handoff` スキル）。触るファイル・禁止事項・受け入れ条件・検証コマンドまで明記する。
2. **ガードレールの前出し**。実行スキルの冒頭に「やってはいけないこと」を置く。軽量モデルは本文を最後まで読まずに走り出すことがあるため。
3. **検証の契約化**（`verify` スキル）。「実行した出力だけを根拠に報告する。実行していないことを完了と言わない」を完了条件に組み込む。

## スキル構成（全11本）

### ライフサイクル上の配置

```
把握      orient                          … 未知のリポジトリを最短で把握する
要件      grill-me / write-a-prd          … 要件と設計判断を詰める・PRD化する
分解      prd-to-issues                   … 薄い縦切りの issue に分解する
受け渡し  plan-handoff                    … 実行者向けの実行指示書を書く（計画者用）
実装      dev-base / tdd / debug          … 実装・TDD・系統的デバッグ
確認      verify / review-diff            … 動かして検証・差分レビュー
設計改善  improve-codebase-architecture   … 設計上の摩擦を見つけて改善する
```

### 新設5本の役割

| スキル | 役割 | 既存との差 |
|---|---|---|
| `verify` | 変更後に実際に動かし、出力を根拠に報告する完了ゲート | tdd は赤緑ループ、verify は最終確認 |
| `plan-handoff` | 計画者が実行者へ渡す実行指示書フォーマット | PRD は人向け、これはモデル実行者向け |
| `orient` | 未知のリポジトリのマップ化 | dev-base の探索を独立した「最初の一手」に |
| `debug` | 再現→切り分け→原因特定の系統的デバッグ | tdd は再現テスト止まり、原因特定の方法論を持つ |
| `review-diff` | 差分のバグ・単純化レビュー | improve-codebase-architecture は広い設計、こちらは目の前の差分 |

## リポジトリ構造

- **単一ソース**: トップレベルの `<skill>/` フォルダ（Codex 向けレイアウト、`agents/openai.yaml` を含む）。
- **生成物**: `.claude/skills/<skill>/` は `scripts/sync-skills.sh` で生成する。手で編集しない。
- **ハーネス設定**: `CLAUDE.md`（Claude Code 向け規約・スキル導線）、`AGENTS.md`（Codex 向け同等規約）、`.claude/settings.json`（権限 allowlist）。

## 実行フェーズ

- **Phase 0**（基盤）: sync スクリプト、CLAUDE.md / AGENTS.md / settings.json、本プラン文書。
- **Phase 1**（新設）: verify / plan-handoff / orient / debug / review-diff の5スキル作成。→ `docs/tasks/T1-new-skills.md`
- **Phase 2**（品質パス）: 既存6スキルの構造統一とガードレール前出し。→ `docs/tasks/T2-existing-skills.md`
- **Phase 3**（合成）: ワークフロー文書と README 更新。→ `docs/tasks/T3-docs.md`

## スキル共通フォーマット

全スキルは次の節構成に揃える。

1. frontmatter（`name` / `description`。description は「いつ使うか」が分かる書き方にする）
2. 冒頭にガードレール（やってはいけないこと）または基本姿勢
3. 進め方（番号付き手順）
4. 出力・報告フォーマット（あれば）
5. 完了条件

語彙は既存スキルに揃える: 縦切り / tracer bullet / deep module / 振る舞い / 観測可能。
