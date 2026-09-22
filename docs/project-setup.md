# 新しいプロジェクトの始め方

このベースはスキル・運用・接続コマンドを含みます。`project-start` で、ローカル複製からGitHub・Linear Projectの新規作成、初期Issueまでまとめて準備できます。アプリ実装、クラウド契約、デプロイは含みません。

## 一式まとめて立ち上げる

`$project-start プロジェクト名はmy-app、目的は○○。GitHubはprivateで、Linearとスキル一式も準備して` のように依頼します。必要な選択だけ確認し、スキルの [手順](../project-start/SKILL.md) とdry-run対応の複製補助を使います。

複製補助は履歴・認証・元の接続情報を持ち込まず、既存フォルダを上書きしません。現在の全スキルを含め、`.agents` と `.claude` の入口も作ります。未コミット内容を含める時は差分の確認が必要です。単にこのスキルを導入するだけでは外部作成を始めません。

## 複製する

GitHubでテンプレートリポジトリとして設定している場合は「Use this template」から新規リポジトリを作成できます。通常のcloneでも使えます。

```sh
git clone https://github.com/dooochi8/dev-base.git my-project
cd my-project
git remote rename origin template
git remote add origin <新しいリポジトリのURL>
./scripts/sync-skills.sh --check
```

`origin` を新規リポジトリへ向けてからpushします。単純なフォルダコピーを使う場合は `.git`・`.linear.json`・`.env*`・認証ファイルを複製しないでください。Gitのcloneでは追跡されていないローカル設定はコピーされません。

## プロジェクトを設定する

1. READMEの製品名・目的・対象者を複製先の内容に置き換える。
2. AGENTS.mdの共通運用は保ち、決定済みの構成や禁止事項を追記する。
3. 既存のLinear Projectを `./scripts/linear discover` で確認する。どれを使うか不明なら所有者へ聞く。
   新規Projectの作成が依頼済みの場合だけ、未接続の新規コピーで `project-create --team-id UUID --name NAME --confirm-create` を使い、返されたProject IDを確認する。
4. APIキーをユーザー領域で用意し、`init --team-id UUID --project-id UUID` で接続する。`init` はLinear上のProjectを作成・変更しない。
5. `doctor` と `list` で接続先・状態・既存Issueを確認する。
6. 製品要件、設計判断、受入条件をdocsへ保存し、最初の機能・成果単位のIssueを起こす。
7. 採用技術に合わせてコードと実行コマンドを追加する。PoC前の候補を採用済みと書かない。

既存のNotion日常タスクは移行しません。機能単位のLinear IssueとGitHub PRを結び、GUI操作や外部設定も完了条件と確認記録を残します。

## 共通部分を検証する

```sh
./scripts/sync-skills.sh --check
python3 -B -m unittest discover -s scripts -p 'test_*.py'
./scripts/linear doctor
```

最初の2つは認証なしで実行できます。`doctor` には認証と実在する接続先が必要です。コピー確認・静的検査は、全Skillの自動発動や実アプリの動作確認を証明するものではありません。
