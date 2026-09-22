---
name: project-start
description: dev-baseを元に新規プロジェクトのGitHubリポジトリ、Linear、共通開発スキル、初期Issueをまとめて準備する。新しい開発環境を一式立ち上げたい時に使う。既存アプリの実装やスキル追加だけの依頼は対象外。
---

# 新プロジェクトを立ち上げる

最小限の選択で、開発を始められるリポジトリを作る。アプリ実装・クラウド契約・本番公開は別作業として扱う。スキルを作成・導入する依頼を、実プロジェクトを作る許可と取り違えない。

## 入力を揃える

会話から既知の値と許可済み範囲を拾い、同じことを聞き直さない。次のうち結果を変える未確定事項だけをまとめて確認する。

- 名前と短い目的。リポジトリ名は安全なslugにし、表示名は日本語でもよい。
- GitHubの所有者と公開範囲。指定がなければ認証済み個人アカウント＋**private**を提案する。組織やpublicを推測で選ばない。名前・所有者・範囲が明示され、一式作成が依頼済みなら再承認は不要。
- LinearのTeamと、既存Projectを使うか同名の新規Projectを作るか。過去プロジェクトのIDは流用せず、現在の一覧から特定する。
- ローカル保存先。希望がなければ `~/dev/<slug>` を提案し、Vaultや既存リポジトリの中へネストしない。

「まずローカルだけ」「pushしない」などの制約があれば優先する。GitHub作成・初回push・Linear作成が依頼に含まれるか曖昧な時は、その外部操作だけを確認し、許可済みのローカル準備は続ける。

## ベースを選び、複製する

1. ユーザー指定のdev-baseを優先する。未指定なら、このスキルの実パスの親がdev-base構成か調べ、次に `~/dev/dev-base` を確認する。製品リポジトリにコピーされた同名スキルを、その製品の複製許可とみなさない。ベースが見つからなければ場所を聞く。古いremote版で黙って代用しない。
2. ベースの `AGENTS.md`、`docs/project-setup.md` とGit状態を確認する。未コミット追加も含めるなら対象差分を確認し、その事実を伝える。元ベースへのcommit/pushや設定変更は行わない。
3. `<このSKILL.mdのあるディレクトリ>/scripts/bootstrap.py` を使う。以下の `SKILL_DIR` / `BASE` / `DEST` は確認した絶対パスに置き換える。

```bash
python3 "$SKILL_DIR/scripts/bootstrap.py" --source "$BASE" --dest "$DEST" --name my-app --description '目的の説明'
# 出力されたファイル一覧・スキル一覧を確認した後に実行する
python3 "$SKILL_DIR/scripts/bootstrap.py" --source "$BASE" --dest "$DEST" --name my-app --description '目的の説明' --apply
```

未コミット内容を含むことを確認済みのベースだけ `--allow-dirty-source` を付ける。既定はdry-runで、既存ディレクトリには空でも上書きしない。Git履歴、remote、認証ファイル、複製元のLinear接続は持ち込まず、正本スキルと共通資料だけをコピーして両クライアントの入口を生成する。

4. 出力先のREADME、AGENTS、`docs/bootstrap.json` とスキル数を再取得する。数を19/20へ固定せず、現在のベースで確認した一覧と照合する。未決の技術は候補・未定と書き、minori_v2の仕様やIDを新製品の決定事項としてコピーしない。

## GitHub・Linearを接続する

外部セットアップを行う時だけ [接続と再開](references/connections.md) を読む。既存の `gh` と複製先の `./scripts/linear` を使い、次の順で進める。

1. 認証・所有者・既存repo/Projectを読み取り確認する。失敗を「存在しない」と見なさない。
2. 未設定の新規コピーでLinear Projectを選択または作成し、`init` → `doctor` → `list`。同じ成果のIssueがなければ、開発環境一式を成果にした初期Issueを1件作る。認証が未準備なら、本文案を `docs/bootstrap-issue.md` に保存して外部部分だけ未完了にする。
3. 新しいGit履歴を初期化し、確定事項・リンク・未確認事項をdocsへ記録する。対象ファイルを確認して初回commit。GitHub新規作成と初回pushまで依頼されている場合だけ実行し、remoteのSHAと公開範囲を読み戻す。以後の開発はIssue付きブランチとPRに切り替える。
4. 初期Issueに成果物・検証・未完了を記録し再取得する。単なる準備手順を多数のIssueに分割しない。固定WIP上限を設けない。

## 検証と引き継ぎ

```bash
bash scripts/sync-skills.sh --check
python3 -B -m unittest discover -s scripts -p 'test_*.py'
./scripts/linear doctor
```

最初の2つは外部書込なしで行う。Linear未接続ならdoctor成功とは報告しない。スキル配置検査と実アプリの試験、自動発動・対話品質の評価を区別する。

完了報告はローカルパス、GitHub URL/公開範囲/初回push、Linear Project/Issue/状態、スキル一覧と件数、検証結果、未完了を短く示す。次の一手は既存要件があれば最初の薄い実装、曖昧なら `grill-me` / `write-a-prd`。すべてのスキルを一斉に実行しない。

Codexの保存済みプロジェクトへの登録は、利用可能な正式操作でできた時だけ完了とする。登録機能がなければフォルダの追加をユーザーに案内する。新しいセッションの作成はユーザーが求めた時だけ行う。

## 失敗した時

作成済みのリポジトリやProjectを自動削除してやり直さない。再実行では既存パス・remote・Project・Issue・コメントを読み、未完了の段階から続ける。名前が同じだけで所有・目的が同じとは判断しない。認証値を表示・複製せず、Issue削除禁止・Notionの日常運用・既存ユーザーファイルを維持する。
