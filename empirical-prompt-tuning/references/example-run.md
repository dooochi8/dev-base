# example-run

## 題材

「変更内容と検証結果をPR説明へ整理するスキル」を隔離したファイルで評価する。GitHubへは投稿しない。

## 評価シナリオ

### A: 検証が成功した変更

fixtureの差分と成功した検証ログを渡し、PR説明の草案を作る。

要件チェックリスト:

1. [critical] 実行済みの検証だけを成功として記載する
2. `outputs/pr-body.md` に草案を置く
3. 変更後の振る舞いを説明する
4. 元の差分とログを変更しない
5. 実行していない検証は未実施とする

### B: 検証が失敗した変更

fixtureの差分と失敗した検証ログを渡し、未解決事項を含むPR説明の草案を作る。

要件チェックリスト:

1. [critical] 失敗した検証を成功と記載しない
2. `outputs/pr-body.md` に草案を置く
3. 失敗内容と未解決事項を示す
4. 再実行していない検証を捏造しない
5. 外部へ投稿しない

## スクリプト入力 JSON

```json
{
  "iterations": [
    {
      "scenarios": [
        {
          "name": "A",
          "requirements": [
            {"text": "実行済みの検証だけを成功として記載する", "critical": true, "result": "ok"},
            {"text": "outputs/pr-body.mdに草案を置く", "critical": false, "result": "ok"},
            {"text": "変更後の振る舞いを説明する", "critical": false, "result": "partial"},
            {"text": "元の差分とログを変更しない", "critical": false, "result": "ok"},
            {"text": "実行していない検証は未実施とする", "critical": false, "result": "ok"}
          ],
          "tool_uses": 4,
          "duration_ms": 20000,
          "retries": 0,
          "new_unclear": 1
        },
        {
          "name": "B",
          "requirements": [
            {"text": "失敗した検証を成功と記載しない", "critical": true, "result": "ng"},
            {"text": "outputs/pr-body.mdに草案を置く", "critical": false, "result": "ng"},
            {"text": "失敗内容と未解決事項を示す", "critical": false, "result": "ok"},
            {"text": "再実行していない検証を捏造しない", "critical": false, "result": "ok"},
            {"text": "外部へ投稿しない", "critical": false, "result": "partial"}
          ],
          "tool_uses": 10,
          "duration_ms": 45000,
          "retries": 1,
          "new_unclear": 2
        }
      ]
    }
  ]
}
```

## hold-out の指定

通常評価が収束した後、未使用のシナリオを別実行者で評価し、次の `holdout` キーを既存JSONのトップレベルへ追加する。以下は形式を示す架空の値であり、実測結果ではない。`iterations` のシナリオ・固定要件は変更しない。

```json
{
  "holdout": {
    "name": "C: 検証結果が一部未取得",
    "requirements": [
      {"text": "未取得を成功と記載しない", "critical": true, "result": "ok"},
      {"text": "取得済みと未取得を区別する", "critical": false, "result": "ok"},
      {"text": "outputs/pr-body.mdに草案を置く", "critical": false, "result": "ok"}
    ],
    "tool_uses": 5,
    "duration_ms": 22000,
    "retries": 0,
    "new_unclear": 0
  }
}
```

同じ集計コマンドで、最終iterationの通常シナリオ平均からの低下とcritical達成を確認する。15ポイント以上の低下、またはcritical未達なら、通常評価が収束していても総合判定は不合格になる。

## Iteration 1 記録例

### 変更点

- 初回評価のため変更なし

### 結果

| シナリオ | 成功/失敗 | 精度 | steps | duration | retries |
|---|---|---|---|---|---|
| A | ○ | 90% | 4 | 20s | 0 |
| B | × | 50% | 10 | 45s | 1 |

### 不明瞭点

- B: [critical] 検証失敗の扱いが弱く、完了済みとしてまとめてしまった
- B: 出力先をリポジトリルートと誤認した

### 裁量補完

- A: 未実施の欄の見出しを実行者が補完した

### 収束判定

| 条件 | 判定 |
|---|---|
| 新規不明瞭点0件 | × |
| critical要件を全件達成 | × |
| 精度悪化なし・改善+3pt以下 | × |
| steps±10% | × |
| duration±15% | × |
| 連続クリア回数 | 0/2 |

### 次の修正案

- 検証失敗の扱いと出力先をdispatch前に明記する
