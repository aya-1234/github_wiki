# 写真自動整理ツール 基本設計書

## 1. システム構成

本システムは以下のレイヤーで構成する。

```text
photo-organizer/
│
├── Presentation Layer
│   ├── CUI
│   └── GUI
│
├── Application Layer
│   └── Organizer Service
│
├── Domain Layer
│   ├── Photo
│   ├── Metadata
│   └── Duplicate
│
├── Infrastructure Layer
│   ├── File System
│   ├── EXIF Reader
│   └── Hash
│
└── OS Layer
    ├── Windows
    ├── macOS
    └── Linux
```

---

# 2. ディレクトリ構成

```text
photo-organizer/
│
├── pyproject.toml
├── .env
├── .env.example
├── README.md
│
├── src/
│   └── photo_organizer/
│       │
│       ├── __init__.py
│       ├── main.py
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py
│       │
│       ├── core/
│       │   ├── organizer.py
│       │   ├── scanner.py
│       │   ├── metadata.py
│       │   ├── duplicate.py
│       │   └── file_operator.py
│       │
│       ├── models/
│       │   ├── photo.py
│       │   └── result.py
│       │
│       ├── os/
│       │   ├── base.py
│       │   ├── windows.py
│       │   ├── macos.py
│       │   └── linux.py
│       │
│       ├── cli/
│       │   ├── commands.py
│       │   └── prompts.py
│       │
│       └── gui/
│           ├── main_window.py
│           ├── settings_window.py
│           └── dialogs.py
│
├── tests/
│   ├── test_scanner.py
│   ├── test_metadata.py
│   ├── test_duplicate.py
│   ├── test_organizer.py
│   └── test_file_operator.py
│
└── build/
```

---

# 3. 技術構成

| 項目        | 採用技術               |
| --------- | ------------------ |
| 言語        | Python             |
| CLI       | argparse / Typer等  |
| GUI       | PySide6            |
| EXIF      | Pillow / exifread等 |
| 設定        | python-dotenv      |
| ハッシュ      | hashlib            |
| ファイル操作    | pathlib / shutil   |
| ログ        | logging            |
| Windows配布 | PyInstaller        |
| macOS配布   | PyInstaller        |
| Linux配布   | PyInstaller等       |

---

# 4. 設定設計

## 4.1 .env

```env
SOURCE_PATH=
DESTINATION_PATH=

DEFAULT_MODE=copy

MOVE_WARNING=true

CREATE_DATE_FOLDER=true

DUPLICATE_ALGORITHM=sha256

SUPPORTED_EXTENSIONS=.jpg,.jpeg,.png,.heic,.heif
```

---

# 5. 設定項目

| 項目                   | 内容          |
| -------------------- | ----------- |
| SOURCE_PATH          | SDカード内の入力元  |
| DESTINATION_PATH     | 写真保存先       |
| DEFAULT_MODE         | copy / move |
| MOVE_WARNING         | 移動警告の有無     |
| CREATE_DATE_FOLDER   | 日付フォルダ自動作成  |
| DUPLICATE_ALGORITHM  | 重複判定方式      |
| SUPPORTED_EXTENSIONS | 対象拡張子       |

---

# 6. 処理フロー

## 6.1 全体フロー

```text
開始
 ↓
設定読み込み
 ↓
入力元確認
 ↓
保存先確認
 ↓
処理モード確認
 ↓
MOVEの場合
 ├─ 警告
 └─ y/n確認
 ↓
写真検索
 ↓
1ファイル取得
 ↓
写真ファイル判定
 ↓
メタデータ取得
 ↓
撮影日時取得
 ↓
保存先yyyy/mm/dd決定
 ↓
保存先ディレクトリ確認
 ↓
ハッシュ計算
 ↓
重複確認
 ↓
重複？
 ├─ YES → スキップ
 └─ NO
       ↓
   COPY / MOVE
       ↓
次のファイル
 ↓
終了
```

---

# 7. CUI設計

## 7.1 初期設定

```bash
photo-organizer init
```

入力：

```text
Source path:
Destination path:
Default mode:
Move warning:
```

設定結果を`.env`へ保存する。

---

## 7.2 実行

```bash
photo-organizer run
```

設定されたデフォルトモードで実行する。

---

## 7.3 コピー

```bash
photo-organizer copy
```

強制的にコピー処理を行う。

---

## 7.4 移動

```bash
photo-organizer move
```

移動モードで実行する。

`MOVE_WARNING=true`の場合：

```text
WARNING

Files will be moved from the source.
Source files may be removed.

Continue? [y/N]:
```

---

## 7.5 ドライラン

将来的な安全機能として以下を実装可能とする。

```bash
photo-organizer run --dry-run
```

実際のファイル操作を行わず、処理予定だけ表示する。

例：

```text
IMG001.JPG
  Source: /SD/DCIM/IMG001.JPG
  Destination: /Pictures/2026/09/24/IMG001.JPG
  Action: COPY

IMG002.JPG
  Action: SKIP
  Reason: DUPLICATE
```

---

# 8. GUI設計

## 8.1 メイン画面

```text
+------------------------------------------------+
| Photo Organizer                                |
+------------------------------------------------+
|                                                |
| Input                                           |
| [ /Volumes/SDCARD/DCIM              ] [Browse] |
|                                                |
| Destination                                     |
| [ /Users/user/Pictures               ] [Browse]|
|                                                |
| Mode                                            |
|   (*) Copy                                     |
|   ( ) Move                                     |
|                                                |
| [Start]                         [Cancel]        |
|                                                |
+------------------------------------------------+
| Progress                                        |
| [########################........] 70%         |
|                                                |
| Processed : 700                                |
| Skipped   : 20                                 |
| Error     : 0                                  |
+------------------------------------------------+
```

---

# 9. GUI設定画面

```text
Settings

Source
[____________________________] [Browse]

Destination
[____________________________] [Browse]

Default mode
(●) Copy
( ) Move

Move warning
[✓] Show warning before move

Hash algorithm
[SHA-256 ▼]

Supported extensions
[.jpg, .jpeg, .png, .heic]

                    [Save]
```

---

# 10. OS対応設計

OS固有処理をApplication Coreから分離する。

```python
class OSAdapter:

    def get_source_devices(self):
        pass

    def open_directory(self, path):
        pass

    def get_default_picture_directory(self):
        pass
```

OSごとに実装する。

```text
OSAdapter
    │
    ├── WindowsAdapter
    ├── MacOSAdapter
    └── LinuxAdapter
```

ただし、通常のファイルコピー・移動処理はOS固有コードにせず、Python標準APIを使用する。

---

# 11. 写真取得設計

入力ディレクトリ以下を再帰的に検索する。

```python
Path(source).rglob("*")
```

ファイルのみを対象とする。

拡張子を確認し、対象画像のみ処理する。

---

# 12. メタデータ設計

撮影日時取得優先順位：

```text
DateTimeOriginal
       ↓
DateTimeDigitized
       ↓
DateTime
       ↓
ファイル更新日時
       ↓
日時不明
```

日時不明の場合は、処理停止ではなくエラーとして記録し、次のファイルへ進む方式を基本とする。

---

# 13. 保存先設計

撮影日時：

```text
2026-09-24 15:30:00
```

の場合：

```text
保存先/
└── 2026/
    └── 09/
        └── 24/
```

へ保存する。

---

# 14. 同名ファイルへの対応

同じファイル名でも内容が異なる可能性がある。

したがって、

```text
ファイル名
```

だけでは重複判定しない。

基本判定：

```text
SHA-256(file)
```

を利用する。

---

# 15. 重複処理

### 同一データの場合

```text
Source:
IMG001.JPG
SHA256 = AAA

Destination:
IMG001.JPG
SHA256 = AAA

Result:
SKIP
```

### 同名だが内容が異なる場合

```text
Source:
IMG001.JPG
SHA256 = AAA

Destination:
IMG001.JPG
SHA256 = BBB

Result:
別ファイルとして扱う
```

この場合のファイル名衝突処理については詳細設計で定義する。

---

# 16. ファイル名衝突

同一フォルダに同名だが異なるファイルが存在する場合、

```text
IMG001.JPG
IMG001_001.JPG
IMG001_002.JPG
```

のようにリネームする。

ただし、元ファイル名を可能な限り保持する。

---

# 17. コピー処理

```text
Source
  │
  ├── Read
  │
  ├── Hash
  │
  ├── Duplicate Check
  │
  └── Copy
        ↓
Destination
```

コピー処理ではSDカード側を変更しない。

---

# 18. 移動処理

```text
Source
  │
  ├── Read
  │
  ├── Hash
  │
  ├── Duplicate Check
  │
  └── Move
        ↓
Destination
```

移動処理は以下の条件を満たした場合のみ実行する。

```text
ユーザー確認
      AND
移動対象ファイル
      AND
コピー先への保存成功
```

---

# 19. エラー処理

以下のエラーを個別に処理する。

| エラー      | 処理       |
| -------- | -------- |
| SDカードなし  | 処理中断     |
| 保存先なし    | 作成       |
| 読み込み失敗   | スキップ＋ログ  |
| EXIF取得失敗 | fallback |
| ハッシュ計算失敗 | スキップ＋ログ  |
| コピー失敗    | エラー＋ログ   |
| 移動失敗     | エラー＋ログ   |
| 権限不足     | エラー表示    |
| ディスク容量不足 | 処理停止     |

---

# 20. ログ設計

ログ例：

```text
2026-09-24 17:00:01 INFO Start
2026-09-24 17:00:02 INFO Source: /SD/DCIM
2026-09-24 17:00:02 INFO Destination: /Pictures

2026-09-24 17:00:03 INFO COPY IMG001.JPG
2026-09-24 17:00:04 INFO SKIP IMG002.JPG DUPLICATE

2026-09-24 17:00:05 INFO Complete
```

---

# 21. 処理結果

処理終了時に以下を表示する。

```text
================================
Photo Organizer Result
================================

Processed : 1000
Copied    : 950
Moved     : 0
Skipped   : 48
Error     : 2

Completed.
================================
```

---

# 22. 配布設計

Windows：

```text
PhotoOrganizer.exe
```

macOS：

```text
PhotoOrganizer.app
```

Linux：

```text
photo-organizer
```

PyInstaller等を使用して単体配布できる構成とする。

---

# 23. Git管理

推奨構成：

```text
.gitignore

.env
__pycache__/
.venv/
dist/
build/
*.spec
```

`.env`はGitへ登録しない。

`.env.example`をGitへ登録する。

```env
SOURCE_PATH=
DESTINATION_PATH=
DEFAULT_MODE=copy
MOVE_WARNING=true
```
