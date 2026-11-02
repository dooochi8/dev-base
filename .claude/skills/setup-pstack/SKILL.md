---
name: setup-pstack
description: このプロジェクトのpstack担当別モデル・推論量を設定する。担当のモデル設定を依頼された時に使う。
---

# pstackの担当設定

[実行対応](../poteto-mode/references/runtime.md) の「プロジェクト設定」と「担当とモデル」を読む。依頼された担当・モデル・推論量を、対象プロジェクトのGit管理外 `.pstack-models.md` へ設定する。

[上流定義](UPSTREAM-SKILL.md) はroleの一覧と書式を確認する資料。グローバルの保存先・include・hook・専用agentの登録手順はこのskills-only移植では使わない。既存値と利用できるモデルを確認し、必要な行だけ更新して同じファイルを読み戻す。設定だけで実際のモデル起動を確認したことにしない。

[上流記録](UPSTREAM.md)
