# 接続と再開

以下は、対象と外部作成がユーザー依頼で確定した場合の手順。変数には確認済みの値を使い、認証キーを引数へ入れない。

## 事前確認

- `gh auth status`、`gh api user --jq .login` と `gh repo view OWNER/REPO --json nameWithOwner,visibility,url,defaultBranchRef` で本人・所有者・repoを確認する。失敗時はHTTPエラーを区別する。認証/通信失敗は不在ではない。
- `./scripts/linear discover` は全Team/Projectを読む。候補が複数なら一意なIDをユーザーと選ぶ。既に `.linear.json` がある再開作業では `doctor` で検証し、設定を上書きしない。
- API権限を変更したりTokenを新規発行したりする必要があれば、その操作だけユーザーへ依頼する。認証値はチャットに貼らせない。

## Linear

`project-create` は**未接続の新規コピーだけ**で使う。既存バインドがあるリポジトリから別のProjectを作らない。同一Teamに同名（大文字小文字・前後空白を正規化）のProjectがあれば書込前に停止する。

```bash
./scripts/linear discover
# 新規作成が依頼済み、同名が存在しない時だけ
./scripts/linear project-create --team-id TEAM_UUID --name 'Project表示名' --confirm-create
# 作成結果のreadBackでID・名前・Teamを確認してから
./scripts/linear init --team-id TEAM_UUID --project-id PROJECT_UUID
./scripts/linear doctor
./scripts/linear list
./scripts/linear create --title '開発環境を初期化する' --state 'In Progress' --description-file docs/bootstrap-issue.md
```

状態は `doctor` の実一覧から選ぶ。標準名がない時に勝手に状態を作らない。初期Issue本文は目的、範囲、受入条件（スキル/安全な接続/GitHub/検証）、依存、結果を含める。製品要件IDがなければ捏造しない。

作成の応答が不明な場合は `discover` で再取得してから判断する。Project作成を自動再送しない。完了時は `comment --id ID --body-file FILE`、`update --id ID --state STATE`、`get --id ID` で結果と状態を記録・確認する。Issue削除コマンドや任意GraphQLは提供しない。

## GitHub

新規ローカルコピーに `.git` がないことを確認して `git init` → `git symbolic-ref HEAD refs/heads/main`。既存repoのHEADをこの方法で変更しない。READMEとdocsに確定した目的・接続先・残Gateを記録し、`git status`、`.gitignore`、追加予定のファイルを確認して初回commitする。認証値・実際の `.linear.json`・`.env` を追加しない。ignore済みの秘密情報を確認のために開かない。

次は**private作成・初回pushまで依頼済み**の例。public/internalの場合は、その指定が確認済みの時だけ対応するフラグへ変える。

```bash
gh repo create OWNER/REPO --private --source /absolute/new-project --remote origin --disable-issues
# remoteと所有者・公開範囲を再確認してから
git -C /absolute/new-project push -u origin main
gh repo view OWNER/REPO --json nameWithOwner,visibility,url,defaultBranchRef,hasIssuesEnabled
git -C /absolute/new-project rev-parse HEAD
git -C /absolute/new-project ls-remote origin refs/heads/main
```

`--disable-issues` は新規repoをLinear正本で使うため。既存repoの設定は勝手に変更しない。branch protection、課金、組織権限、GitHub App導入、ライセンス選択、クラウドdeployは別の判断が必要。ベースにTemplate設定がなくてもローカル複製経由なら始められる。

同名repoが既にある場合は作成・上書きしない。作成直後に通信が切れた場合も `gh repo view` と `git remote -v` を読み、所有・空/既存履歴・今回の作成結果を照合する。GitHub存在・公開範囲が確定する前にpushしない。force-push、削除、既存remoteの無断置換はしない。

## 保存と再開

`docs/bootstrap.json` はローカル複製の出典・複製元ファイルのhashであって、GitHub/Linearの完了証拠ではない。外部URL/ID、Issue、実行結果、未完了段階は `docs/bootstrap-status.md` へ記録する。Tokenは書かない。再開時は記録だけで成功判定せず、外部リソースを再取得する。README・AGENTSの製品向け調整や後の編集でhashが異なるのは正常であり、初期状態へ巻き戻さない。

## コマンド仕様の根拠

作成時（2026-09-22）に確認した一次資料。仕様が変わった場合は実CLIヘルプと公式資料を照合する。

- [GitHub CLI repo create](https://cli.github.com/manual/gh_repo_create)
- [Linear公式GraphQL schema](https://github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql) の `ProjectCreateInput` / `ProjectPayload`
