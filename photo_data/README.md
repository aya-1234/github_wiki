# Photo Organizer

SDカードなどの写真を撮影日ごとの `yyyy/mm/dd` フォルダへコピー、または移動するPythonアプリケーションです。重複判定にはSHA-256を使います。標準モードはコピーです。

## 開発環境

Python 3.14以上とuvを用意してから、依存関係を同期します。

```bash
uv sync --extra dev --extra build
cp .env.example .env
uv run photo-organizer init
```

## CUI

```bash
uv run photo-organizer status
uv run photo-organizer run
uv run photo-organizer copy --source /path/to/DCIM --destination /path/to/Pictures
uv run photo-organizer move
uv run photo-organizer gui
```

UbuntuでGUIが `xcb-cursor0` 不足により起動しない場合は、システムへ `sudo apt-get install libxcb-cursor0` を実行してください。これはPython依存関係とは別のOSライブラリです。

`move` は設定で警告を無効にしていない限り、確認に `y` と答えた場合だけ開始します。データが同一の重複写真はスキップし、移動モードでも重複を理由に入力元を削除しません。

`.env` の `DATE_FALLBACK` は `file_mtime`（既定：更新日時を使う）または `skip` を選べます。HEIC/HEIFのEXIF読み取りは環境内のPillow対応状況に従います。

## 検証

```bash
uv run ruff check src tests
uv run mypy src tests
uv run pytest
uv run photo-organizer --help
```

## 配布ビルド

各OS上でそれぞれビルドしてください。PyInstallerの成果物はOS間で共有できません。

```bash
uv run pyinstaller --clean --noconfirm photo_organizer.spec
```

成果物は `dist/` に出力されます。設定ファイルは実行時に作成し、配布物へ秘密情報を含めないでください。
# photo_data
