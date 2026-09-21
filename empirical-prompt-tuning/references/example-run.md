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
            {"critical": true, "result": "ok"},
            {"critical": false, "result": "ok"},
            {"critical": false, "result": "partial"},
            {"critical": false, "result": "ok"},
            {"critical": false, "result": "ok"}
          ],
          "tool_uses": 4,
          "duration_ms": 20000,
          "retries": 0,
          "new_unclear": 1
        },
        {
          "name": "B",
          "requirements": [
            {"critical": true, "result": "ng"},
            {"critical": false, "result": "ng"},
            {"critical": false, "result": "ok"},
            {"critical": false, "result": "ok"},
            {"critical": false, "result": "partial"}
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
