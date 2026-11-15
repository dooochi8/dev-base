---
name: maintain-verification-skill
description: 既存の検証手順と機能一覧をコード・実操作に照らして更新する。verifyの内容が実態に合うか監査する時に使う。
---

# maintain-verification-skill

[実行対応](../poteto-mode/references/runtime.md) を先に読む。このセッションで読んでいれば再読不要。
続いて [上流の手順](UPSTREAM-SKILL.md) を読み、依頼に該当する参照だけを開いて実行する。上流のツール・モデル・専用agent・保存先は実行対応へ読み替える。成果と検証の証拠を日本語で報告する。

## dev-baseでの対象

対象は `verify/project.md` と `verify/features/`。共通の `verify/SKILL.md` と、他のスキルは編集範囲に含めない。`docs/statecharts/` に図がある機能は、図の遷移と機能マップの手順の対応も照合し、食い違いを報告する。直した後に `./scripts/sync-skills.sh` と `--check` を実行し、`docs/verification.md` の根拠を更新する。

[上流記録](UPSTREAM.md)
