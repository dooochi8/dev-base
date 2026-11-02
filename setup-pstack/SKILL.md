---
name: setup-pstack
description: このプロジェクトのpstack担当別モデル・推論量を設定する。担当のモデル設定を依頼された時に使う。
---

# pstackの担当設定

[実行対応](../poteto-mode/references/runtime.md) の「担当とモデル」を先に読む。上流の Models とシート例にある Claude、GPT、Gemini の識別子は書かない。

設定ファイルは、作業中リポジトリのルートにある Git 管理外 `.pstack-models.md` だけである。`~/.claude/pstack-models.md`、`~/.codex/pstack-models.md`、ホームの `AGENTS.md` は変更しない。

Grok に揃える依頼でファイルが無いときは、全 role をセッション継承にする。別モデルへは切り替えない。

```markdown
# pstack model configuration

feature, refactoring: inherit-parent
bug-fix: inherit-parent
perf-issue: inherit-parent
hillclimb: inherit-parent
judgment and prose: inherit-parent
strongest judgment: inherit-parent
how explorer: inherit-parent
how explainer: inherit-parent
why investigators: inherit-parent
why synthesizer: inherit-parent
reflect tooling: inherit-parent
reflect judgment, divergent, synthesizer: inherit-parent
arena runners: inherit-parent
arena cross-judge pool: inherit-parent
swarm workers: inherit-parent
architect runners: inherit-parent
interrogate reviewers: inherit-parent
default effort: session
```

Cursor の Task で、そのセッションの `model` 一覧に Grok があるときだけ、ユーザーが指定した role へその識別子を書いてよい。2026-11-02 に Cursor クラウドエージェントの Task 引数として確認した形は、`grok-4.7` と `cursor-grok-4.6` に、任意で `-low` / `-medium` / `-high` / `-xhigh`、さらに任意で `-fast` を付けるものである。Codex CLI と Claude Code の Agent では Grok の識別子を確認していない。確認できない識別子は書かず、`inherit-parent` のままにする。

既存ファイルは必要な行だけ更新し、同じファイルを読み戻す。設定を書いただけではモデルの起動確認にしない。

[上流定義](UPSTREAM-SKILL.md) は role 名と書式の資料である。グローバル保存先、include、hook、専用 agent の登録は、この移植では実行しない。

[上流記録](UPSTREAM.md)
