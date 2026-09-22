# Linear開発運用

開発の状態・優先順位・完了条件はLinear、仕様・ADR・試験はdocs、コード・レビューはGit/GitHubへ置きます。日常業務は従来のNotion等に残します。同時進行数の固定上限はありません。

## 接続

Python 3.9以降の標準ライブラリだけで動作します。認証は `LINEAR_API_KEY` を優先し、なければ `~/.linear_token` の先頭の非空行を使います。Tokenファイルは裸のキーまたは `LINEAR_API_KEY=...` 形式に対応し、shellとして実行しません。

```sh
./scripts/linear discover
./scripts/linear init --team-id TEAM_UUID --project-id PROJECT_UUID
./scripts/linear doctor
```

`discover` は参照可能なTeamとProjectを全ページ取得します。名前を確認してUUIDを選んでください。`init` は所属を読み取って検証し、既存の `.linear.json` があれば上書きせず停止します。キーは保存しません。接続先はリポジトリルート基準で読み、実行するカレントディレクトリには依存しません。

新しいProjectの作成を依頼された場合は、未接続の新規コピーで `./scripts/linear project-create --team-id TEAM_UUID --name '表示名' --confirm-create` を使えます。参照可能なTeam・アーカイブを含む同名Projectを確認してから作成し、ID・名前・所属を再取得します。自動接続はしないので、返されたIDで `init` してください。既存設定がある場合や同一Teamに同名がある場合は書込せず停止します。作成応答が不明なら自動再送せず `discover` で確認します。

`.linear.example.json` は書式例です。実際の `.linear.json` はGit管理外に置き、新しいプロジェクトで再設定します。APIキーをコマンド引数・PR・Issue・ノートに貼り付けないでください。

## 操作

```sh
./scripts/linear list
./scripts/linear list --state Todo
./scripts/linear get --id TEAM-123
./scripts/linear create --title '機能名' --state 'In Progress' --label Feature --description-file /path/to/issue.md
./scripts/linear create --title '独立した子成果' --parent TEAM-123 --description-file /path/to/child.md
./scripts/linear update --id TEAM-123 --state 'In Review'
./scripts/linear comment --id TEAM-123 --body-file /path/to/result.md
./scripts/linear cancel --id TEAM-123 --reason '取りやめ理由'
./scripts/linear cancel --id TEAM-123 --state Duplicate --reason 'TEAM-456と重複'
```

- `list` は未アサイン・完了・アーカイブも含めて全ページ取得する。アーカイブを除く時は `--active-only`。
- 状態名はTeamごとに異なるため `doctor` で確認する。createの既定は `Todo`。存在しない状態や曖昧なラベルは拒否する。
- `--priority` は0（未指定）、1（Urgent）、2（High）、3（Normal）、4（Low）。
- `--label` は指定した既存ラベル1件への置換。ラベル指定なしのupdateは既存ラベルを維持する。
- 取消・重複は `cancel --reason` を使う。理由コメントの読み戻し後に状態を更新する。既に同じ取消状態なら重複コメントを作らない。
- create/updateはIssueを、commentは作成したコメントIDとIssueを再取得して返す。LinearのMarkdown正規化があるため、本文は戻り値でも確認する。
- `get` のコメントは先頭50件とページ情報を返す。残りがある場合はLinear UIで確認する。全件取得済みとは扱わない。
- Project Milestoneとblocks関係はLinear UIで設定・確認する。このCLIに任意GraphQLの抜け道は設けない。

## Issueと開発

機能・成果単位で起票し、単なる実装手順は本文チェックリストへ置きます。担当・依存・検証・再開の単位が分かれる時だけSub-issueにします。内容は `templates/linear-issue.md` を使い、要件IDとTest IDがある場合は記録します。まだないIDを捏造しません。

同じ成果の既存Issueを確認してから作成し、着手・受入確認待ち・完了の状態を実態に合わせます。PRにIssue IDを記載し、必要な実環境確認が済んでからDoneへ進めます。GitHub Issuesには重複登録しません。

## 削除禁止と失敗時

IssueはAPI・CLI・スクリプト・MCP等の自動化から削除しません。完全削除が必要ならユーザー本人がLinear UIで行います。このCLIは操作の許可リストを使い、delete/remove/purge/issueDeleteを通信前に拒否します。

これはCLIと運用ルールによる制限であり、APIキー自体の権限を変更するものではありません。別ツールからの削除が技術的に不可能になったとは扱いません。

Team/Project外のIssueや親Issueは書込前に拒否します。HTTP/APIエラー、タイムアウト、読み戻し失敗を0件・成功と扱わず、自動再送もしません。失敗したら現在のIssue/コメントを確認し、作成・コメントの重複やcancelの部分反映を確かめてから続けます。
