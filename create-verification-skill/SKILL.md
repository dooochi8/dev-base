---
name: create-verification-skill
description: アプリ・CLI・サービスを実際の操作で検証するプロジェクト固有の手順を作る。動作確認の入口がない時に使う。
---

# create-verification-skill

[実行対応](../poteto-mode/references/runtime.md) を先に読む。このセッションで読んでいれば再読不要。
続いて [上流の手順](UPSTREAM-SKILL.md) を読み、依頼に該当する参照だけを開いて実行する。上流のツール・モデル・専用agent・保存先は実行対応へ読み替える。成果と検証の証拠を日本語で報告する。

## dev-baseでの置き場所

上流の `.claude/skills/verify/` は、トップレベルの `verify/` に読み替える。共通の `verify/SKILL.md` は置き換えず、次のファイルを追加して `./scripts/sync-skills.sh` で同期する。

- `verify/project.md`: Launch / Doctor / Drive / Evidence / Cleanup / Helpers。雛形は `templates/harness/verify-project.md`。
- `verify/features/README.md` と機能ごとのファイル: 雛形は `templates/harness/features/`。4つのH2は上流の英語のまま保つ。
- 繰り返す操作は検証用CLIとして `scripts/` に置き、`verify/project.md` の Helpers に呼び出し方を書く。

作成後に `docs/verification.md` のランタイム検証スキル・機能マップ・検証用CLIの行を、実行した証拠付きで更新する。状態の多い機能は `user-statechart` の図と遷移を機能マップの手順へ対応させる。

[上流記録](UPSTREAM.md)
