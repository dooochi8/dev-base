# 追加スキルの導入元

2026-09-21時点のユーザー環境にあるスキルを、dev-baseのトップレベル正本へ取り込みました。元のインストール先は変更していません。

| 名前 | 導入元 | dev-baseでの調整 |
|---|---|---|
| grilling | ユーザー環境のCodex版。上流はmattpocock/skills | Vault前提を外し、既存grill-meとの使い分けを追加 |
| show-me | ユーザー環境のHumanLayer由来版 | 日本語化し、特定アプリのopen操作を利用可能なプレビューへ置換 |
| empirical-prompt-tuning | ユーザーの共有スキル | 補助スクリプト・参照文書も同梱。相対パス化、評価と導入の区別、収束判定の入力/必須要件確認 |
| linear-workflow | この会話で確定した開発運用 | minori_v2固有名・ID・絶対パスを除き、複製先ごとの設定へ変更 |

grillingの取得元commit等は `grilling/references/upstream.md` に保存しています。show-meの上流参照は `https://github.com/humanlayer/skills`。この記録は元の著作権・ライセンスを変更するものではありません。

同期検査はファイル配置と参照の検査です。Codex/Claudeでの全スキルの自動発動、実ユーザーの対話、反復評価の収束は別の実行証拠が必要です。
