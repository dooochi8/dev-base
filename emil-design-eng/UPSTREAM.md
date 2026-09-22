# 導入元

- Repository: https://github.com/emilkowalski/skills
- Path: `skills/emil-design-eng/SKILL.md`
- Commit: `85e8e2363b713506e1d5b6e07a0eb2da66be1bc3`
- SHA256: `ffbe68e6007fb42cb8149f089b400a1ca007d59ba23e8948e2be4476f3175939`
- License: MIT。上流ルートのLICENSEを著作権表示ごと同梱。

## dev-baseでの構成

- skill-installerでcommitを指定して取得した原文を `references/upstream.md` へ改変せず保存。
- `SKILL.md` は日本語の入口。原文の章への読み分け、利用範囲、実装・レビュー・検証の進め方を整理。
- 名前 `emil-design-eng` は維持。初回の定型英語応答で待機する指示は採用せず、依頼された具体的な作業を進める。
- 上流の設計思想・事例・コード例は原文に保持。バージョン依存のAPI・ブラウザ対応・性能の断定は公式資料と実測で確認する運用にする。
- 依存パッケージ・グローバル設定・通知は導入時に追加しない。既存UIの全面刷新も自動では行わない。

今回収録するのは上流が中心スキルと位置づける `emil-design-eng`。`animate`、`review-animations`、Swift/Expo向けなど別の12スキルは同梱しない。既存の `show-me` は説明の図解、`smart-docs` はコードの文書化、本スキルは利用者向けUIの実装・レビューを担当する。
