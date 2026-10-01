---
name: browser-evidence
description: Webアプリを実ブラウザで検証し、操作動画・画面・実行結果を残してPRへ掲載するときに使う。クラウドとローカルで同じ操作シナリオを実行し、S3/R2への保存とPR掲載は明示した接続先で行う。
---

# ブラウザ検証とPR証跡

実装した挙動を実ブラウザで確かめ、レビューする人が操作と結果を追える証跡を残す。

## 境界

- リポジトリのAGENTS.md、開発手順、Linear運用を先に確認する。
- 検証は専用のローカル環境と合成データで行う。実利用者のデータや本番の認証を録画しない。
- アプリ側の起動・終了はPlaywrightのwebServerで管理する。起動失敗、検証失敗、動画未生成を成功として扱わない。
- Trace、Cookie、storageState、APIレスポンス、サーバーログは公開対象にしない。アップロードはmanifestに記録された動画とPNGだけ。
- 動画はソース管理に入れない。公開処理は既定でdry-run。保存先・認証・許可された通信先を確認してから実行する。
- PRへ掲載する証跡は、そのPRの現在のhead SHAに一致する、コミット済みのソースで取り直す。
- CIの公開処理はdefault branchの信頼済みスクリプトで行い、PRのコードをSecret付きで実行しない。

## 進め方

1. [導入・接続手順](references/setup.md)を読み、アプリの起動コマンドと完了条件を設定する。
2. 変更した操作を、role・labelを使うPlaywrightのシナリオとして表す。準備とfixture注入は操作による検証と区別する。
3. `node browser-evidence/scripts/run.mjs`を実行する。途中の画面を確認したい場合は失敗画面・動画を観察する。問題があれば修正し、同じ経路を再実行する。
4. 出力先の`manifest.json`・`summary.md`・`assets/`を確認する。成功にはassertionと動画の両方が必要。
5. PR用の最終headで再実行し、`publish.py --dry-run`で掲載予定のURLと本文を確認する。
6. 設定済みのS3/R2へ`--publish`で保存する。PR掲載も行う場合は`--comment --repo OWNER/REPO --pr NUMBER`を指定する。保存完了とPRのheadを確認してから既存の証跡コメントを更新する。
7. テスト結果、動画URL、head SHA、未確認項目をPRとLinearへ記録する。iOS実機、メール配送、外部API等をローカルWeb検証済みの範囲に含めない。

## 完了条件

実際に操作した結果、動画の生成、検証したhead SHAを説明できること。外部保存・PR掲載が未実行なら、それぞれ未実行と報告する。
