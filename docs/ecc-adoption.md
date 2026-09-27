# ECCの採用範囲

dev-baseは [ECC](https://github.com/affaan-m/ECC) の開発手法を選んで統合している。ECCプラグイン全体をインストールした状態ではない。技術スタックが未確定でも複製できること、CodexとClaudeで同じ正本を使えること、GPT-6 Astraで作業を完了できることを優先した。

- 確認日: 2026-09-27 JST
- 参照commit: `e482e579415fde18357cafce70f177ae19fd7f03`
- ライセンス: MIT / Copyright (c) 2026 Affaan Mustafa
- 同梱ライセンス: [ECC LICENSE](third-party/ecc/LICENSE)。移植したスキルにも個別に同梱する。

## 対応表

| ECCの要素（同commit内のパス） | dev-baseの対応 | 調整 |
|---|---|---|
| `skills/search-first/SKILL.md` | [search-first](../search-first/SKILL.md) | 日本語化。既存コードを先に調べ、必要時に一次資料で比較。研究専用エージェントやMCPを必須にしない |
| `skills/security-review/SKILL.md`, `rules/common/security.md` | [security-review](../security-review/SKILL.md) | 差分と信頼境界に限定。特定フレームワークや認証方式を強制せず、拒否ケースと証拠を重視 |
| `skills/verification-loop/SKILL.md` | [verify](../verify/SKILL.md)へ統合 | ビルド・型・lint・テスト・セキュリティ・差分のうち該当項目を選択。未実施・対象外を区別 |
| `skills/strategic-compact/SKILL.md` | [長い作業の再開](codex.md#長い作業の再開) | 中断前に状態を記録し再開時に照合。特定ツールの圧縮コマンド・自動メモリ・タイマーは導入しない |
| `.codex/config.toml` | [プロジェクト設定](../.codex/config.toml) | GPT-6 Astraの5段階（low / medium / high / xhigh / max）を選択でき、既定はxhigh。モデル以外の設定は持ち込まない |
| `rules/common/testing.md` | 既存の `tdd` / `debug` を継続 | 振る舞い中心のred-greenは維持。一律80%や全変更でのE2E・強制委譲は採用しない |

planner・code-reviewer等の役割は、既存の要件・設計・差分レビュースキルで扱う。実行環境に存在しないエージェント名を指示へ持ち込まない。

## 含めていないもの

- 全言語・フレームワーク向けスキルの一括コピー。複製先で採用技術が決まってから選ぶ。
- グローバルプラグイン導入、MCPサーバー追加、通知コマンド、権限変更、自動hooks。
- 会話・操作履歴の自動収集、instinctsやメモリの自動更新。
- 既存プロジェクトへの自動配布、ECC本体の自動更新。

完全なECCプラグインが必要な場合は [上流のCodex導入案内](https://github.com/affaan-m/ECC#codex-app-and-cli) に従って別途検討する。今回の `search-first` / `security-review` と同名のスキルがあるため、二重に読み込ませず、どちらを正本にするか決める。

## 更新するとき

上流のcommitと対象ファイルの差分を確認し、この対応表と各スキルの `UPSTREAM.md` を更新する。ECCの自動同期スクリプトをこのリポジトリやユーザーの設定へそのまま実行しない。

トップレベル正本を変更後、`scripts/sync-skills.sh` で両クライアントへ同期し、同期検査と `scripts/test_project_start.py` を含む既存試験で複製を確認する。設定変更はCodexの読込も確認する。試験結果の範囲を越えて、実モデルの品質改善や動作確認済みとは報告しない。
