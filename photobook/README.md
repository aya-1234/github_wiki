# Photobook

`photo/` に画像を置き、CUIコマンドで正方形のミニマルなフォトブックPDFを生成します。

## 必要環境

- Python 3.10 以降
- Pillow
- ReportLab
- PyYAML

## インストール

プロジェクトのルートで仮想環境を作成し、開発モードでインストールします。

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e .
```

## 使い方

1. 写真を `photo/` に入れます（サブディレクトリも検索します）。
2. 必要なら `config.yaml` を編集します。
3. 次を実行します。

```bash
photobook build
```

既定の出力先は `artifact/photobook.pdf` です。同名ファイルが存在する場合、既定では上書きせずエラーになります。

設定ファイルを初期化する場合：

```bash
photobook init
```

上書きを明示的に許可する場合：

```bash
photobook build --overwrite
```

設定ファイルを明示する場合：

```bash
photobook build --config config.yaml
```

## 初期仕様

- 正方形 210 × 210 mm
- 表紙1ページ + 写真1枚につき1ページ
- EXIF撮影日時を優先して昇順に並べる
- EXIF日時がない写真はファイル更新日時を使用
- 画像の向きをEXIF Orientationに基づいて補正
- 写真は縦横比を維持し、ページ内に収める
- キャプションなし
- 入力画像は変更しない

## 注意

- 現バージョンはJPEG、PNG、WebP、TIFF、BMPを対象とします。HEIC/HEIFは別途対応が必要です。
- PDFの「210 × 210 mm」はページ寸法です。印刷所に入稿する場合は、塗り足し・トンボ・ICCプロファイルなどの入稿仕様を別途確認してください。
- EXIF撮影日時がない場合はファイル更新日時を使います。これは撮影日時と一致するとは限りません。
