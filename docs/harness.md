# ハーネス設計：決定論的制約と検証

エージェントの出力品質を、指示文ではなくコードベースの構造と機械的な検査で保つための設計。Lauren Tan（poteto、pstack-claudeの作者）の講演「slopをgoldに変える」の考え方を、このベースと複製先へ適用する。

## 原則：逆ピラミッド

エージェントの環境へ投資する順序は次の通り。上ほど再現性が高く、信頼できる。

1. **コード自体**: API設計、アーキテクチャ、リファクタリング。誤用しにくい形にして、正しい書き方を既定にする。
2. **決定論的な検査**: lint、型、コンパイラ、依存境界、テスト、`harness-check`。
3. **検証**: 実行時の検証（実際に動かす、DevTools、スクリーンショット・動画）と形式的な検証（モデル検査、プロパティベーステスト）。
4. **文章**: AGENTS.md、スキル、ルール。判断が必要なことだけを書く。

エージェントを修正したら、その修正を AGENTS.md の一文ではなく、1か2の層へ変換する。文章は強制できず、言い訳の置き場にもなるため。

## コードベースは庭

エージェントはコードベースを最大の入力として、既存のパターンを真似る。回避策、非推奨コード、技術的負債を残すと、次のエージェントがそれを「確立したパターン」として増やす。

- 新規発生を止める検査を先に入れる。
- その後で既存の違反を掃除する。
- 掃除した分は、元へ戻らないように固定する。

この3段を `harness-check` のラチェットが担う。

## harness-check

`scripts/harness-check.mjs` は依存のない Node スクリプトで、正本はこのリポジトリにある。複製先へはファイルごと写す。

- `harness.config.json`: 検査対象（`include` / `exclude`）とルール（`id`、正規表現 `pattern`、許可する場所 `allow`、ルール単位の対象 `include`、失敗時の `message`）。
- `harness-baseline.json`: 導入時点の既存違反をファイル・ルールごとの件数で記録した上限。

| 状況 | 結果 |
|---|---|
| baseline にないファイルで違反 | 失敗（場所と根本原因の直し方を表示） |
| baseline の件数を超えた | 失敗 |
| baseline より減った | 失敗（`--prune` で上限を下げるまで） |
| baseline と一致 | 成功 |

- `--init`: baseline がない時だけ作る。二度目は拒否する。
- `--prune`: 上限を現在の件数まで下げる。
- `--self-test`: 各ルールの `examples.bad` で必ず失敗し、`examples.good` では通ることを確かめる。例のないルールも失敗にする。ファイルと baseline は読まない。
- `--adopt <rule>`: 設定に新しく足したルールの既存違反を一度だけ記録する。採用済みのルールは `adopted` に残り、二度目は拒否する。ルールの追加は人間の判断で行う。

これ以外に上限を上げる操作はない。

失敗時の `message` は、症状を隠す方法ではなく根本原因の直し方を書く。エージェントはこの文を読んで修正するため、ここがプロンプトの代わりになる。

### 既定のルール（TypeScript / React）

`templates/harness/harness.config.json` を出発点にする。

| id | 防ぐもの | 正しい置き場・直し方 |
|---|---|---|
| `raw-effect` | 生の `useEffect` / `useLayoutEffect` | 派生値・イベントハンドラ。外部同期は `src/platform/` の名前付きフック |
| `raw-timer` | `setTimeout` 等によるタイミング調整 | データフローの修正。時間が仕様なら `src/platform/` の抽象 |
| `explicit-any` | `any` による型消去 | 境界で `unknown` を受けてパースする |
| `type-escape` | `@ts-ignore`、`as unknown as` | 型定義かデータの形を直す |
| `lint-suppression` | lint 無効化コメント | コードを直すか、ルール変更を提案する |
| `excuse-comment` | 「後で直す」「回避のため」等のコメント | 根本原因を直すか、Issue に記録して判断を仰ぐ |
| `code-comment` | コードコメント全般（`/// <reference` 等の指示子を除く） | 名前・型・関数分割で意図を表し、制約は lint・型・テストで表す。例外は人間が判断する |

`allow` に入れた場所（既定は `src/platform/`）だけが危険APIを扱える。そこに置いた抽象はテストで振る舞いを示す。

ディレクトリ境界は、ルール単位の `include` で表す。例：ドメイン層から React を import させない。

```json
{ "id": "domain-imports-ui", "pattern": "from [\"']react", "include": ["src/domain/**"], "message": "..." }
```

パッケージ単位の境界は、依存グラフの検査（minori_v2 の `check:boundaries` 等）を使う。正規表現では表せない検査（非nullアサーション、hooks の依存配列等）は oxlint などの AST ベースの lint に任せる。

## 複製先への導入手順

`project-start` で作った新規プロジェクトには、手順1・2と CI が最初から入っている。既存のプロジェクトへ入れる時は次の順で進める。

1. `scripts/harness-check.mjs` と `templates/harness/harness.config.json` をプロジェクトのルートへ写し、`include` と `allow` を構成に合わせる。
2. `node scripts/harness-check.mjs --init` で baseline を作り、件数を確認してコミットする。
3. `check:harness` を検証コマンド（`verify`）と CI に入れる。CI の雛形は `templates/harness/workflow.yml`（試験・`--self-test`・検査の3段）。
4. AGENTS.md に行動規範の節を置く（このリポジトリの AGENTS.md と同じ内容で、検証コマンドだけ置き換える）。
5. 既存違反を少しずつ直し、`--prune` で baseline を縮める。

## エージェントのミスをルールにする手順

手順の正本は [`mistake-to-rule`](../mistake-to-rule/SKILL.md) スキル。`reflect` と `principle-encode-lessons-in-structure` も、構造化する項目をこの手順へ渡す。

1. 人間がエージェントの出力を直したら、ミスを1文と、最小の悪例・正しい例の1行ずつにする。
2. 繰り返すミスなら、最も強い仕組みを選ぶ。表現できない型・API、コンパイラ設定、AST lint、`harness-check` ルール、正規の補助関数と禁止API、実行時検査・テスト、文章の順。
3. `harness-check` のルールには `message`（根本原因の直し方）と `examples`（悪例・良例）を書き、`--self-test` と実際のミスの再現で失敗することを示す。
4. 人間がルールの追加を承認したら `--adopt <rule>` で採用済みにする。既存の違反は同じ変更で直すことを優先し、残る分だけを `--adopt` が一度だけ記録する。PR に件数を書き、人間のレビューを受ける。
5. 同じ内容の注意書きが AGENTS.md やスキルにあれば消す。機械化できないものだけを短く書く。

## 段階的な発展

| 段階 | 内容 | 次へ進む前提 |
|---|---|---|
| 1. 制約 | lint、型、境界、`harness-check`、既存負債の掃除 | なし |
| 2. 検証 | ランタイム検証スキル、機能マップ、検証用CLI、PRの検証成果物、プロパティベーステスト、状態遷移図、重要フローのモデル検査 | 段階1 |
| 3. 自動化 | クラウドエージェントでの並列実行、リリースごとのファジングと修正PR、強い検証を通った変更の自動マージ | [段階3の設計](harness-phase3.md) の前提条件 |

内側のループが slop を生むうちに自動化すると、slop が増えるだけになる。段階3は段階1・2の後に行う。

## 段階2：検証パイプライン

段階1が「書いてはいけない形」を止めるのに対し、段階2は「変更が利用者に見える振る舞いとして正しい」ことを、エージェント自身が証明できるようにする。複製先での導入状況は `docs/verification.md`（雛形は `templates/harness/verification-plan.md`）に記録する。

| 要素 | 置き場所（複製先） | 作る・保つスキル | 雛形 |
|---|---|---|---|
| ランタイム検証スキル | `verify/project.md` | `create-verification-skill` / `maintain-verification-skill` | `templates/harness/verify-project.md` |
| 機能マップ | `verify/features/` | 同上 | `templates/harness/features/` |
| 検証用CLI | `scripts/` | `create-verification-skill`、`principle-build-the-lever` | なし（プロジェクト固有） |
| PRの検証成果物 | PR本文 | `verify`、`principle-prove-it-works` | `templates/harness/pr-evidence.md`、`.github/PULL_REQUEST_TEMPLATE.md` |
| 状態遷移図 | `docs/statecharts/` | `user-statechart` | `user-statechart/references/template.md` |
| プロパティベーステスト | `*.property.ts` 等 | `tdd`、`user-statechart` | なし |
| モデル検査 | 判断を `docs/verification.md` に記録 | 下の判断基準 | なし |

`verify` は完了ゲートであり、上の要素はその入力になる。`verify/SKILL.md` は共通のまま保ち、プロジェクト固有の手順は同じフォルダの `project.md` と `features/` に足す。

### 導入手順

1. **最初の利用者向け機能が動いた時点で、ランタイム検証スキルを作る。** `create-verification-skill` を使い、起動・Doctor・操作・証拠・後片付けを `verify/project.md` に書く。生成した手順を一度最後まで実行し、証拠が後片付けの後も残ることを確かめる。実行していない手順は下書きとして扱う。
2. **機能マップを作る。** 利用者向けの機能を1機能1ファイルで `verify/features/` に置く。最初は主要な3〜5機能でよい。各ファイルは利用者のすべての入口と、観測できる最終状態を書く。機能を追加・変更するPRは、同じPRで機能マップも直す。定期的に `maintain-verification-skill` で実態と照合する。
3. **検証用CLIを作る。** 機能マップの操作を、エージェントが一つのコマンドで実行できる道具にする（例: `scripts/verify-cli doctor`、`scripts/verify-cli drive <feature-id>`）。起動・操作・証拠の保存を毎回手で組み立てさせない。出力は人間とエージェントの両方が読める形にし、終了コードで成否を返す。
4. **PRに検証成果物を付ける。** PR本文の「検証」に、決定論的な検査の結果と、機能IDごとの操作・期待・結果・証拠（スクリーンショット、動画、ログ、ARIAスナップショット）を載せる。UIの変更は変更前後を並べる。検証できなかった項目は理由と残る確認を書く。
5. **状態遷移図を作る。** 状態が3つ以上ある、読み込み中・失敗・取り消し・オフラインがある、または状態のバグを直したフローは、`user-statechart` で利用者視点の図にし、コードと照合する。図とコードの食い違いは所見として扱い、図に合わせてコードを読み替えない。
6. **プロパティベーステストを入れる。** 図の規則（不変条件）と、純粋な変換（パース・集計・単位変換・直列化の往復）を、任意の入力で成り立つ性質として書く。状態機械はランダムな操作列を与える形（TypeScript なら fast-check の `fc.commands`）にする。失敗した入力は縮小された最小例として回帰テストに残す。ファイル名は `*.property.ts` にし、`harness.config.json` の既定の `exclude` と揃える。
7. **モデル検査を判断する。** 下の基準で、テストでは届かないフローだけを選ぶ。

### モデル検査の判断基準

次の3つが揃うフローだけ、モデル検査（TLA+ 等）を検討する。一つでも欠けるなら、状態遷移図とプロパティベーステストで十分とする。

1. **順序の組み合わせが問題になる。** 並行する操作、再試行、時間切れ、複数の端末・利用者・プロセス、オフラインからの再同期、分散したロックやリース。
2. **壊れた時の被害が大きい。** データの消失・重複、課金、権限、元に戻せない外部送信。
3. **テストで届きにくい。** 壊れる順序がまれで、例示テストやランダムな操作列でも再現しにくい。

採用する時は、性質を利用者の文と被害の文で1つずつ書き、壊した版で失敗することを示し、検査の範囲（上限・前提・省いたもの）を `docs/verification.md` に記録する。上流 pstack の `statechart` と `create-formal-verification-skill` はこの用途の道具だが、まだ採用していない（[採用範囲](pstack-adoption.md) を参照）。採用前は、判断と範囲の記録までを段階2の完了とする。

### 段階2の完了条件

- `docs/verification.md` の段階2の各行が「導入済み」か「対象外（理由）」になっている。
- 直近のPRが、機能IDごとの振る舞いの証拠を載せている。
- `maintain-verification-skill` を一度実行し、機能マップと実際の操作が一致している。
