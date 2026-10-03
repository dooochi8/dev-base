# pstack-claudeの採用範囲

HIRANO-426。dev-baseの標準フローをpstack-claudeへ移行した。既存名のdev-baseもpoteto-modeへ接続し、既存の計画・検証・UI・Linearスキルは補助として使う。

## 固定した出典

- Repository: https://github.com/michael-denyer/pstack-claude
- Commit: `b1f7a460cc52eecc2d913313a307d6e22bb440ff`
- Version: `0.9.63`
- 取得・採用日: 2026-10-03 JST
- 原作: Lauren Tan。移植と追加: Michael Denyer。cursor-team-kit由来部分: Cursor。
- [MITライセンス](third-party/pstack-claude/LICENSE)、[cursor-team-kitのMIT](third-party/pstack-claude/LICENSE-cursor-team-kit)、[NOTICE](third-party/pstack-claude/NOTICE.md)、[技能別の出典](third-party/pstack-claude/NOTICE-skills.md)。

54本すべてのスキル、23 playbook、各参照と補助スクリプトを保持した。元の入口SKILL.mdは各トップレベルの `UPSTREAM-SKILL.md`、その他のファイルは元の相対配置のまま保持する。154ファイルのSHA256は [manifest](pstack-manifest.json) で検査する。日本語のSKILL.mdと実行対応はdev-base固有の移植部分。

`tdd` はpstack版を標準にした。旧入口は `tdd/references/legacy-dev-base.md` に履歴として保存する。既存の他のスキルとEmilスキル群は保持し、同じ工程を二度実行しない。

## 実行環境への移植

[実行対応](../poteto-mode/references/runtime.md) が上流のツール・モデル・保存先・運用を読み替える。各日本語入口が先にこの対応表を読む。

- skills-onlyとしてトップレベル正本を同期する。上流のネイティブplugin manifest、SessionStart hook、Claude専用agent、Pi拡張、Codex slash stubは導入しない。
- AGENTS.mdを標準入口の選択元とし、CLAUDE.mdからも同じ規約を読む。プラグインの登録・hookの信頼・全モデルへのアクセスが確認済みとは扱わない。
- 上流の固定モデルではなく、セッション設定の継承とユーザーの指定を優先する。担当別設定は依頼された時だけ `.pstack-models.md` に置き、Gitと新規プロジェクト複製へ持ち込まない。
- 開発管理はLinear、仕様と判断はdocs、コードとレビューはGit/GitHub。読み取りの相談・レビューだけで外部操作やPR作成を起動しない。
- verifyのトップレベル正本と既存の必須検査を保持し、プロジェクト固有の実操作手順を加えられる。個人の全履歴・メモリ・グローバル設定を探索・更新しない。

## 補助スクリプトと依存

採用は実行依存のインストールを意味しない。検査前に利用可能なランタイムと必要なコマンドを確認する。

| 対象 | 主な依存と範囲 |
|---|---|
| スキル選択・参照・既存同期・複製 | 既存のshell / Python。ネットワークなしで配置を検証できる |
| check-plan / check-playbooks / resume / transcript等のmjs | Node.js。対象に応じたローカルデータが必要 |
| orchestrator / watch-pr等のTypeScript | bun。PR操作はghと認証、上流のstack操作にはgt等が必要 |
| UIの実操作 | セッションで利用可能なブラウザ・アプリ操作。権限と対象アプリが必要 |

Node.jsの検査が通ってもbunの長期運用・実PR監視・マージ・全アプリの操作を確認したことにはならない。

## 検査と更新

```sh
python3 scripts/check_pstack.py
bash scripts/sync-skills.sh --check
python3 -B -m unittest discover -s scripts -p 'test_*.py'
```

上流更新は新しいcommitを確認し、変更された原文・付属資料・playbook・依存・NOTICEを比較してから適用する。manifestのハッシュだけ書き換えて検査を通さない。日本語入口と実行対応の整合、同期と複製、独立したシナリオ評価を行う。上流更新ツールや全ランタイムの生成器を移植したとは扱わない。

更新時も `UPSTREAM-SKILL.md` と付属資料の無改変保持を基本とする。原文を直接修正する必要があれば、その理由と対象を出典へ記録し、manifestの変更をレビューする。

配置・同期・参照・複製の検査と、独立シナリオの評価は別の証拠。全playbookのライブ動作・自動発動・品質向上・反復評価の収束は、それぞれ実行証拠が必要。

## 今回の検証結果（2026-10-03 JST）

| 対象 | 結果と根拠 |
|---|---|
| 移植・既存運用・複製 | `python3 -B -m unittest discover -s scripts -p 'test_*.py'` の62試験が合格。原文の改変検知、範囲外参照の拒否、実際の新規コピー、個人設定の除外、必須参照の保持を含む |
| 原文・ライセンス・同期 | `check_pstack.py` と `sync-skills.sh --check` が合格。154原文ファイルと112ライセンス等のハッシュ、両クライアントへの配置を照合 |
| スキルの入口 | skill-creatorの `quick_validate.py` で54本が合格。上流の `check-playbooks.mjs` も合格 |
| 独立した読み取り評価 | 別担当が調査のplaybookを使い、モデル設定と複製範囲を説明。外部操作・書込は実施せず |
| 独立した修正評価 | 隔離した送料計算のバグで、5000円の境界の失敗を再現して修正。4999・5000・5001円の3試験が合格。実リポジトリ・外部サービスの変更はなし |
| 上流の補助スクリプト | `PATH="/usr/bin:$PATH" bun test poteto-mode/scripts` は166試験中165合格、1失敗。下記の制限を残す |

上流の `watch-pr/transport.test.ts` の「cancels an in-flight command at the CLI deadline」は、タイムアウトの状態と制限時間の検査には合格したが、起動したプロセスを確認するpidファイルが存在せず `ENOENT` で失敗した。単独再実行も同じ結果だったため、実行中コマンドの中断は未検証とする。原文と試験条件を変更して合格扱いにはしていない。

実PRの継続監視・自動マージ、長時間のorchestrator、Claude専用hooks、全54スキル・全23 playbookの実操作は未検証。今回の独立評価2件は、反復的な指示評価の収束や複数モデルによる評価を証明しない。
