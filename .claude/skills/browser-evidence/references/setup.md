# 導入と接続

## プロジェクトへの導入

新規dev-base複製にはこのスキルと実行部品が含まれる。既存プロジェクトには`browser-evidence/`を正本としてコピーし、Codexの`.agents/skills/browser-evidence`は`../../browser-evidence`へのリンクにする。Claude用は正本から生成する。`dev-base`への絶対パスを残さない。

Node 20以降、Python 3.9以降と、プロジェクト内の固定バージョン`@playwright/test`が必要。導入例は`pnpm add -Dw --save-exact @playwright/test@1.58.2`。ブラウザと録画用ffmpegは`pnpm exec playwright install --with-deps chromium`で準備する。インストール時にも環境の通信許可を確認する。既存Chromiumを使う場合は`BROWSER_EVIDENCE_EXECUTABLE_PATH`に実行ファイルを指定できる。配布先に接続できないクラウドでは`BROWSER_EVIDENCE_SYSTEM_FFMPEG`に導入済みffmpegの絶対パスも指定する。runnerは今回のrun内にだけ録画ツールへのリンクを作り、システムや既存のブラウザcacheは変更しない。

1. `templates/playwright.evidence.config.mjs`をルートへコピーし、起動コマンド・URL・テストディレクトリをプロジェクトに合わせる。
2. `.artifacts/`を`.gitignore`へ追加する。rawには失敗時の詳細が残るため、公開・Git管理の対象にしない。
3. `tests/browser/*.spec.mjs`に実操作とassertionを置く。成功画面は`testInfo.attach`でPNGを添える。動画は成功・失敗とも自動録画される。
4. `node browser-evidence/scripts/run.mjs`を実行する。最新出力先は`.artifacts/browser-evidence/latest.json`に記録される。

同じrunnerとシナリオをクラウド・ローカル・CIで使う。ポートは固定して既存サーバーを再利用しない。別のアプリや古いコードを検証したまま成功にしない。

## S3 / R2

アプリ利用者の添付用バケットとは別の、レビュー証跡用バケットを用意する。このハーネスはバケット作成、公開権限変更、Cloudflareへのdeployを実行しない。

| 設定名 | 内容 | 配置 |
| --- | --- | --- |
| `EVIDENCE_S3_ENDPOINT` | R2: `https://ACCOUNT_ID.r2.cloudflarestorage.com`、S3: `https://s3.REGION.amazonaws.com` | Variables |
| `EVIDENCE_S3_BUCKET` | 証跡用バケット名 | Variables |
| `EVIDENCE_PUBLIC_BASE_URL` | バケット内のkeyを直接読めるHTTPSの基底URL。例: `https://evidence.example.com` | Variables |
| `EVIDENCE_S3_REGION` | R2は`auto`、S3は実際のregion | Variables |
| `EVIDENCE_KEY_PREFIX` | 例: `minori-v2`。既定は`browser-evidence` | Variables |
| `EVIDENCE_S3_ACCESS_KEY_ID` | 証跡用バケットへの書込用キー | Secrets |
| `EVIDENCE_S3_SECRET_ACCESS_KEY` | 上記キーのsecret | Secrets |
| `EVIDENCE_S3_SESSION_TOKEN` | 一時AWS認証を使う場合だけ | Secrets |

キーはチャット・Git・Issue・コマンド引数に入れない。バケットの対象prefixへのPutObjectに限定した認証を使う。動画の閲覧範囲は保存先で決める。この版は署名付き閲覧URLの発行には対応せず、指定した公開基底URLへのリンクを作る。公開URLの閲覧可否・保持期間・削除ルールは保存先で設定する。

クラウド環境ではS3 API endpoint、動画の公開URL、GitHub APIへの通信許可が必要。公開処理はPython標準ライブラリのSigV4 PUTを使い、既存のHTTPSプロキシとCA trustを維持する。署名用の実キーが必要で、プロキシの認証プレースホルダーは署名キーに使えない。

```sh
# MANIFESTには実際のrun内のmanifest.json、HEAD_SHAには検証したcommitを指定。
python3 browser-evidence/scripts/publish.py \
  --manifest "$MANIFEST" --expected-sha "$HEAD_SHA" --dry-run

# 設定済みの保存先へ公開する。PRが指定headのままであることを確認してコメントを更新。
python3 browser-evidence/scripts/publish.py \
  --manifest "$MANIFEST" --expected-sha "$HEAD_SHA" \
  --publish --comment --repo OWNER/REPO --pr 123
```

dry-runに認証キーは不要。接続先・バケット・公開URLは必要。出力`pr-body.md`には未実行と明記される。公開時はcleanなcommitの録画のみ受け付け、PUT後に各公開URLのHTTP HEADとContent-Typeを確認する。保存失敗や閲覧できないURLを公開済みと報告しない。部分的に保存されたobjectは残るため、保存先の保持ルールで回収する。

## CIの分離

アプリを実行するPR workflowはread-only・Secretなし。`assets/`と`manifest.json`だけをActionsの成果物へ渡す。raw・trace・Cookie・サーバーログは渡さない。

公開workflowは`workflow_run`で起動し、default branchのこのスクリプトを実行する。同一リポジトリのPR、現在のhead SHA、入力ファイルの型・サイズ・checksumを確認する。forkのPRは公開しない。権限は`contents: read`、`actions: read`、`pull-requests: write`。Secretは公開jobだけに渡す。`pull_request_target`でPRコードをSecret付き実行しない。

`templates/publish-browser-evidence.yml`を`.github/workflows/`へコピーする。capture workflow名は`Browser evidence`、成果物名は`browser-evidence`に揃える。GitHub Environment `browser-evidence`へ上のVariables/Secretsを設定し、Repository Variable `BROWSER_EVIDENCE_PUBLISH_ENABLED=true`で有効化する。設定前は公開jobをskipする。PR操作にはGitHub Actionsのtoken、手元では設定済みの`gh`認証を使う。

PRコメントは実行者が作った`<!-- browser-evidence:report -->`コメントを更新する。保存できてもPRのheadが進んだ場合は掲載を停止し、新しいheadで録画し直す。GitHub上の外部動画はリンクで掲載する。GitHubのインライン再生は保証せず、動画URLをブラウザで開いて確認する。
