---
name: linear-workflow
description: この開発リポジトリのLinear Issueを取得・作成・更新し、実装や検証結果を結びたい時に使う。新しい複製先のTeam/Project接続設定も扱う。
---

# Linear開発運用

まずリポジトリルートの `docs/linear.md` を読み、`./scripts/linear doctor` で接続先を確認する。未設定なら `discover` で既存Team/Projectを読み、複製先のProjectを一意に判断できない時だけユーザーへ確認する。別プロジェクトの設定を流用しない。

## 作業の流れ

1. `list` で同じ成果の既存Issueを確認し、存在すれば `get --id ID` で読む。
2. 実装・修正の依頼でなければ、読み取りだけで終える。
3. 既存Issueがなければ、目的・対象範囲・完了条件・要件ID/試験ID・参照/依存を本文にする。`templates/linear-issue.md` を使える。
4. `create --description-file FILE` で起票し、読み戻されたIDと内容を確認する。親がある場合は `--parent ID` を指定する。
5. 着手状態へ更新し、`codex/<Issue-ID>-<内容>` のブランチで実装と検証を行う。進行件数の固定上限は設けない。
6. `comment --body-file FILE` に変更・検証・未確認事項・成果物URLを記録する。
7. 必要な検証が完了したら完了状態へ、人の受入確認が必要ならレビュー状態へ更新して読み戻す。PRがマージされただけでは完了と判定しない。

状態名は `doctor` の結果に合わせる。用意されていないラベルや状態を勝手に作らない。GUIや外部サービスの変更も、URL・ID・件数・内容を再取得して照合する。

## 境界

- 操作入口は `./scripts/linear`。設定外のTeam/Projectへ書き込まない。
- IssueをAPI・CLI・MCP等の自動化経由で削除しない。取りやめ・重複は `cancel --reason` で履歴を残す。完全削除はユーザー本人のLinear UI操作に限る。
- 認証情報をIssue・文書・Gitへ保存しない。
- 通信失敗や読み戻し失敗の後は重複・現在値を確認してから再試行する。
- Notionの日常業務は移行しない。仕様はリポジトリのdocs、コード・レビューはGit/GitHubで管理する。
- 通常の実装手順を細切れに起票しない。機能・成果単位を基本に、担当・依存・検証・再開の単位が違う時だけSub-issueへ分ける。
