# GitHub Wiki Importer

Markdown、PDF、Word（`.docx`）、Excel（`.xlsx`）、PowerPoint（`.pptx`）を読み込み、編集・プレビュー後に PR 用の Markdown を保存するローカル Web アプリです。PR のマージ後、GitHub Actions が Wiki に新規ページを追加します。既存ページは上書きしません。

## 必要なもの

- Python 3.14 と [uv](https://docs.astral.sh/uv/)
- Git
- Poppler の `pdfinfo` と `pdftotext`（Ubuntu/Debian では `poppler-utils`）
- 公開先の GitHub Wiki。Wiki を有効にし、GitHub 上で最初のページを作成してください。
- PR の作成に使う GitHub 認証。Wiki 公開用の認証は後述の Actions secret に設定します。

## 起動

```bash
uv sync
uv run python main.py
```

ブラウザで `http://127.0.0.1:8000` を開きます。対応ファイルを指定し、ページ名・本文を確認して「PR 用 Markdown を保存」を押します。`wiki-pages/` に作成されたファイルをブランチにコミットし、PR を作成してください。

## PR 審査後に Wiki へ公開

GitHub Actions で公開する場合、先に対象リポジトリの Wiki を有効にして、GitHub の画面から初期ページを 1 件作成してください。リポジトリの Actions secret に `WIKI_PUSH_TOKEN` を登録します。GitHub Wiki の Git リポジトリへ書き込める personal access token を使用してください。個人リポジトリでは classic PAT の `repo` スコープを利用できます。トークンをソースや PR 本文には記載しません。

`main` に「PR 必須」「1 人以上の承認」「`validate` ステータスチェック必須」のルールセットまたはブランチ保護を設定してください。これを設定しないと、`main` への直接 push でも公開ワークフローが動きます。GitHub の[ルールセット設定](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository)で設定できます。

書類をレビュー用 Markdown に変換します。次の例は同梱の [test.pdf](test.pdf) から作ったページです。

```bash
uv run python -m scripts.stage_wiki_page test.pdf --title PDF-Import-Test-2026-10-19
```

生成先は `wiki-pages/PDF-Import-Test-2026-10-19.md` です。本文と警告を確認してから、PDF と Markdown、`.github/workflows/publish-wiki.yml`、`scripts/` の変更を通常のリポジトリのブランチにコミットし、PR を作成します。PR の検証は新規ページの形式・サイズを確認し、既存の審査用ページの変更・削除を拒否します。PR の段階では Wiki に公開しません。

PR を `main` にマージすると、Actions がそのマージで追加された `wiki-pages/*.md` のみを Wiki に新規登録します。同名ページが Wiki に存在する場合やプッシュが競合した場合は失敗し、既存ページは上書きしません。結果は GitHub Actions の `Review and publish Wiki pages` で確認できます。複数ページを一度に追加した場合、途中で失敗すると先に成功したページは公開済みになります。

Secret の未設定などで初回の公開が失敗した場合は、設定を直して同じ Actions 実行を再実行してください。既に一部のページだけ公開された場合は、同名ページのエラーになるため、公開済みページを確認してから残りを個別に処理します。

このワークフローは Actions の実行環境から GitHub Wiki に接続します。ローカル環境の GitHub 接続制限や `gh` の認証状態は Actions の公開には引き継がれません。PR の作成・マージには別途 GitHub への接続と権限が必要です。旧来の直接公開 API は標準では無効です。明示的に `ALLOW_DIRECT_WIKI_PUBLISH=1` を設定した場合だけ有効になり、PR 審査を経ないため通常運用では使用しません。

## 制約

- 1 回に 1 ファイル、20 MiB 以下。公開本文は 2 MiB 以下。PDF は 100 ページ以下。
- PDF は埋め込み文字のみ抽出します。画像だけの PDF、OCR、添付ファイルの移送には対応しません。表や段組みは崩れる可能性があります。
- Word は段落・見出し・表、Excel はシートごとの値を表、PowerPoint はスライド順の文字を Markdown に変換します。画像・図形・グラフ・コメント・書式・Excel の数式そのものは移送しません。Excel の数式セルは保存済みの計算結果があればその値を使います。変換結果を原本と照合してください。
- 対応する Office ファイルは新形式の `.docx` / `.xlsx` / `.pptx` です。旧形式の `.doc` / `.xls` / `.ppt`、マクロ付き形式、パスワード付きファイルには対応しません。圧縮ファイルは展開後 50 MiB・2000 項目までです。
- Markdown の相対リンクや画像は参照先を警告表示します。編集後も警告を更新します。添付ファイルは自動登録されないため、公開前に参照先を確認してください。
- 新規ページのみ追加します。`Home`、`_Sidebar`、`_Footer` および同名の既存ページは変更しません。
- 同名ページや公開中の更新競合が起きた場合は再確認してください。プッシュが時間切れになった場合は、再試行前に Wiki を確認してください。
- サーバーはローカル利用専用です。複数人で共有するサーバーには配置しないでください。

## 確認

```bash
uv run python -m pytest -q
```

画面スクリプトのヘッドレス DOM テストには Node.js 22 以降を使います。

```bash
node tests/test_ui.mjs
```

ローカル Git Wiki を使った実行証跡と、実行データに基づく画面再現画像は次のコマンドで作り直せます。画像は実ブラウザのスクリーンショットではありません。

```bash
uv run python -m scripts.build_demo_report
```

初期の直接公開経路をローカル Wiki で検証した記録は [実働確認レポート](docs/実働確認レポート.md) を参照してください。現在の標準経路は上記の PR 審査です。

設計と進捗は [docs](docs/概要設計書.md) と [タスク一覧](docs/tasks_1.md) を参照してください。
