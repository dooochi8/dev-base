# GPT-6 Astraで開発する

dev-baseのCodex既定は `.codex/config.toml` の `gpt-6-astra` / `xhigh`。通常の開発はpstack-claudeベースのpoteto-modeが調査・設計・担当分離・実装・レビュー・実行検証を進める。これは既存環境の推論量を維持する運用上の選択で、全タスクで最速・最適と評価した結果ではない。

## 設定の使い方

信頼済みプロジェクトではCodexが `.codex/config.toml` を読み込む。信頼状態や組織の管理設定によっては適用されない。CLIの明示指定やアプリで選択したモデル・推論設定がある場合はそちらを確認する。既存のチャットのモデルを、このファイルの追加だけで変更したとは扱わない。

Astraの `low` / `medium` / `high` / `xhigh` / `max` の5段階に対応する。ECC由来の手順・スキル・完了条件は全段階で共通とし、ユーザーが明示した推論量を尊重する。既定の `xhigh` に戻すためだけの設定変更や再起動は行わない。

プロジェクトディレクトリで、CLIのモデルと推論量を明示して起動する:

| 推論量 | 起動コマンド |
| --- | --- |
| low | `codex -m gpt-6-astra -c 'model_reasoning_effort="low"'` |
| medium | `codex -m gpt-6-astra -c 'model_reasoning_effort="medium"'` |
| high | `codex -m gpt-6-astra -c 'model_reasoning_effort="high"'` |
| xhigh | `codex -m gpt-6-astra -c 'model_reasoning_effort="xhigh"'` |
| max | `codex -m gpt-6-astra -c 'model_reasoning_effort="max"'` |

指定した推論量はその起動に適用され、リポジトリやグローバルの設定ファイルを書き換えない。明示指定がない場合は、信頼済みプロジェクトで `codex` を起動すると既定の `xhigh` を使う。

[Codexの設定仕様](https://learn.chatgpt.com/docs/config-file/config-reference)では、プロジェクト内の `.codex/config.toml` に書いた `profile` / `profiles` は無視される。このリポジトリにはそれらを置かず、CLIの明示指定を使う。

アプリではモデルをGPT-6 Astraにし、画面に表示される推論量から選ぶ。リポジトリの設定によってアプリの選択肢が増えるわけではない。選択肢がない場合は利用環境・アカウントの対応状況を確認する。Astraが使えない環境では、使えるモデルと要件を確認し、別モデルを黙って選ばない。

モデル設定だけを同梱し、権限、承認、MCP、通知、hooks、グローバル設定は変更しない。`project-start` の複製補助は `.codex/config.toml` だけを対象にし、Codexの認証・履歴・その他ローカルファイルを持ち込まない。設定ファイル自体にも認証情報・個人の絶対パスを追記しない。

## 指示とスキル

依頼には目的、対象、制約、完了条件を示す。AGENTS.mdは共通の境界、スキルはその作業で必要な手順を持つ。単純な修正でPRD・全体マップ・引継ぎを作る必要はない。

- 新しい依存・連携・共通機能を足す時は `search-first`。
- 振る舞いの変更・バグ再現には既存の `tdd` / `debug`。
- 認証・入力・秘密情報等の境界を変える時は `security-review`。
- 完了判断は `verify`。必要な検証が通ったら、同じ検査を繰り返さず成果を提示する。

pstackのplaybookが必要な担当分離を選ぶ。上位指示と実行環境が許す範囲で分担し、各担当のモデル・推論量は指定がなければセッション設定を継承する。上流のClaude名やパネル構成は固定しない。[実行対応](../poteto-mode/references/runtime.md)で担当とツールの読み替えを確認する。所有ファイル・成果・依存関係を分け、同じ対象への書込を競合させない。

## 長い作業の再開

中断・引継ぎ・コンテキスト整理が必要になったら、既存のIssueや実装メモへ次の事実だけ残す。通常の小さな修正で追加ファイルを作らない。

```markdown
目的・受入条件:
Issue / branch / 作業ディレクトリ:
変更したものと現在の差分:
確定した判断・禁止事項:
検証したコマンド・結果・対象リビジョン:
未検証・失敗・保留の理由:
次の一手・必要な入力:
```

再開時は記録と現在のGit状態・対象ファイルを照合する。作業中の出力や未検証の結果を完了と読み替えない。秘密情報や会話全体を保存せず、自動的な記憶の書換え、学習用送信、定時の強制圧縮は導入しない。

## 根拠と検証の限界

2026-09-27に確認したOpenAIの一次資料:

- [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra): モデルIDと推論設定。
- [Codex設定リファレンス](https://learn.chatgpt.com/docs/config-file/config-reference): モデル・推論量・プロファイルの設定。
- [Astra向けのスキルと指示の見直し](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra): 短く正確な起動条件、必要な資料だけ読む構成、明確な作業範囲と完了条件。

設定の構文・読込と複製試験は、モデルの実応答・アカウントでの利用可否・全スキルの自動発動を保証しない。実タスクの性能差を測る場合は、同じ受入条件の代表タスクで変更前後を別途比較する。
