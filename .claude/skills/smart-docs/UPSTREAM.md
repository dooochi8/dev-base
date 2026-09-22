# 導入元

- 上流リポジトリ: https://github.com/sopaco/deepwiki-rs
- 上流パス: `skills/smart-docs`
- 導入元に記録されたcommit: `27dbd3ed74535213e7c40be8abcdcec4145bebf2`
- 導入元: ユーザー環境の共有smart-docs（上流版へ日本語の発動条件とCodex互換の注意を加えたもの）
- ライセンス: MIT。元の著作権表示と条件は [LICENSE](LICENSE) に保持。

## dev-baseでの移植

- 本文を日本語へ整理し、個人Vaultの保存先・絶対パスへの依存を除去。
- 概要・C4構成・処理フロー・モジュール詳細の作成手順を保持し、構成例をreferencesへ分離。
- 既存文書の保護、根拠と推測の区別、図の構文確認と描画確認の区別を保持。
- orient / show-meとの使い分け、導入依頼と実行依頼の区別を追加。
- Claude用のツール指定をrg検索と既存文書の編集に合わせて調整。実行環境の権限を優先。
- 上流のグローバルインストーラとClaude専用のREADME/QUICKSTARTは同梱しない。配置・同期・使い方はdev-baseのREADMEと同期処理に統一。

この記録は導入元のローカルファイルに基づく。上流の最新版を取得したという意味ではない。元の共有スキルは変更していない。
