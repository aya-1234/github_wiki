# 写真自動整理ツール 詳細設計書

## 1. モジュール構成

```text
main.py
 │
 ├── config
 │     └── settings.py
 │
 ├── core
 │     ├── scanner.py
 │     ├── metadata.py
 │     ├── duplicate.py
 │     ├── file_operator.py
 │     └── organizer.py
 │
 ├── models
 │     ├── photo.py
 │     └── result.py
 │
 ├── cli
 │     ├── commands.py
 │     └── prompts.py
 │
 ├── gui
 │     ├── main_window.py
 │     ├── settings_window.py
 │     └── dialogs.py
 │
 └── os
       ├── base.py
       ├── windows.py
       ├── macos.py
       └── linux.py
```

---

# 2. 設定管理

## 2.1 Settings

```python
class Settings:
    source_path: str
    destination_path: str
    default_mode: str
    move_warning: bool
    create_date_folder: bool
    duplicate_algorithm: str
    supported_extensions: list[str]
```

---

# 3. Photoモデル

```python
class Photo:
    source_path: Path
    filename: str
    extension: str

    captured_at: datetime | None

    year: int | None
    month: int | None
    day: int | None

    file_size: int
    hash_value: str | None
```

---

# 4. Resultモデル

```python
class ProcessResult:
    processed: int
    copied: int
    moved: int
    skipped: int
    errors: int
```

---

# 5. Scanner

## 5.1 目的

入力元から対象となる画像ファイルを取得する。

## 5.2 インターフェース

```python
class PhotoScanner:

    def scan(self, source: Path) -> list[Path]:
        ...
```

## 5.3 処理

```text
source
 ↓
再帰検索
 ↓
file?
 ↓
extension?
 ↓
対象画像
```

---

# 6. MetadataReader

## 6.1 目的

画像から撮影日時を取得する。

```python
class MetadataReader:

    def get_capture_datetime(
        self,
        path: Path
    ) -> datetime | None:
        ...
```

---

# 7. EXIF取得

優先順位：

```text
EXIF DateTimeOriginal
       ↓
EXIF DateTimeDigitized
       ↓
EXIF DateTime
```

取得結果：

```python
datetime(
    year=2026,
    month=9,
    day=24
)
```

---

# 8. 日時フォールバック

EXIF情報が存在しない場合：

```text
EXIF
 ↓
なし
 ↓
ファイル更新日時
 ↓
使用
```

ただし、設定によって以下も選択可能とする。

```text
DATE_FALLBACK=file_mtime
DATE_FALLBACK=skip
```

---

# 9. DestinationResolver

## 9.1 目的

写真の撮影日時から保存先を決定する。

```python
class DestinationResolver:

    def resolve(
        self,
        destination: Path,
        captured_at: datetime
    ) -> Path:
        ...
```

例：

```python
destination = Path("/Pictures")

captured_at = datetime(2026, 9, 24)

result:
Path("/Pictures/2026/09/24")
```

---

# 10. ディレクトリ作成

```python
target_dir.mkdir(
    parents=True,
    exist_ok=True
)
```

既に存在する場合は何もしない。

---

# 11. DuplicateDetector

## 11.1 目的

完全同一ファイルを判定する。

```python
class DuplicateDetector:

    def calculate_hash(
        self,
        path: Path
    ) -> str:
        ...

    def is_duplicate(
        self,
        source: Path,
        destination: Path
    ) -> bool:
        ...
```

---

# 12. SHA-256

基本アルゴリズム：

```python
hashlib.sha256()
```

大容量ファイルを考慮し、全ファイルを一度にメモリへ読み込まない。

```python
with open(path, "rb") as f:
    while chunk := f.read(1024 * 1024):
        sha256.update(chunk)
```

1MB単位で読み込む。

---

# 13. 重複判定最適化

全ファイルのSHA-256を毎回計算すると処理時間が増加するため、以下の順序で判定する。

```text
ファイル存在？
 ↓
ファイルサイズ一致？
 ↓
サイズ不一致 → 非重複
 ↓
サイズ一致
 ↓
SHA-256比較
 ↓
一致 → 重複
```

これにより不要なハッシュ計算を減らす。

---

# 14. FileOperator

## 14.1 コピー

```python
class FileOperator:

    def copy(
        self,
        source: Path,
        destination: Path
    ) -> None:
        ...
```

内部では安全性を考慮したコピーを行う。

---

# 15. 移動

```python
def move(
    self,
    source: Path,
    destination: Path
) -> None:
    ...
```

移動前に対象ファイルの存在を確認する。

移動後に保存先ファイルの存在を確認する。

---

# 16. コピーの安全性

コピー処理では、

```text
SDカード
   │
   │ READ ONLY
   ↓
アプリケーション
   │
   │ WRITE
   ↓
保存先
```

という考え方で処理する。

アプリケーションからSDカードへ書き込むAPIを使用しない。

---

# 17. 移動の安全性

移動では単純な

```python
shutil.move()
```

だけに依存せず、処理結果を確認する。

基本フロー：

```text
Source exists?
 ↓
Destination exists?
 ↓
Duplicate?
 ↓
Destination directory exists?
 ↓
Copy/Move
 ↓
Destination exists?
 ↓
Success
```

---

# 18. 重要：重複時の削除ルール

重複ファイルが見つかった場合：

```text
コピー元
        ↓
重複
        ↓
SKIP
```

を基本とする。

**重複したからという理由だけでSDカード側のファイルを削除しない。**

特にコピー・移動を問わず、重複削除は別の明示的な機能として扱う。

将来的に削除機能を追加する場合は、

```text
--delete-duplicates
```

などの明示的なオプションを設ける。

---

# 19. Organizer

全処理を統括する。

```python
class Organizer:

    def run(
        self,
        source: Path,
        destination: Path,
        mode: str
    ) -> ProcessResult:
        ...
```

---

# 20. Organizer処理詳細

```text
1. Source確認

2. Destination確認

3. PhotoScanner実行

4. 写真1件取得

5. MetadataReader

6. DestinationResolver

7. mkdir

8. DuplicateDetector

9. 重複ならSKIP

10. 重複なし

11. mode確認

12. COPY / MOVE

13. Result更新

14. 次の写真

15. 完了
```

---

# 21. CUIコマンド

## 21.1 init

```bash
photo-organizer init
```

## 21.2 run

```bash
photo-organizer run
```

## 21.3 copy

```bash
photo-organizer copy
```

## 21.4 move

```bash
photo-organizer move
```

## 21.5 status

```bash
photo-organizer status
```

設定を表示する。

---

# 22. CUI移動確認

```text
========================================
WARNING
========================================

Move mode is enabled.

Files on the source may be removed.

Source:
E:\DCIM

Destination:
D:\Pictures

Continue? [y/N]:
```

入力：

```text
y
```

の場合：

```text
Continue.
```

それ以外：

```text
Operation cancelled.
```

---

# 23. GUI処理

GUIからはCoreを直接呼び出す。

```text
GUI
 ↓
Organizer
 ↓
Scanner
 ↓
Metadata
 ↓
Duplicate
 ↓
FileOperator
```

GUI側にファイル整理ロジックを実装しない。

これによりCUIとGUIで同じ処理エンジンを利用できる。

---

# 24. GUIスレッド

大量の写真を処理するため、GUIのメインスレッドで直接処理しない。

```text
GUI Main Thread
      │
      └── Worker Thread
              │
              └── Organizer
```

処理中もGUIがフリーズしないようにする。

---

# 25. GUIプログレス

WorkerからGUIへ進捗を通知する。

```text
processed
total
current_file
status
```

例：

```text
Processing:

IMG_1024.JPG

850 / 1200

[#####################-----] 70%
```

---

# 26. GUI警告

移動モード選択時：

```text
┌──────────────────────────────┐
│ 警告                         │
├──────────────────────────────┤
│ 移動モードでは、SDカード上の │
│ 写真が移動されます。         │
│                              │
│ 元のデータがなくなる可能性が │
│ あります。                   │
│                              │
│ □ 今後この警告を表示しない   │
│                              │
│ [キャンセル] [実行]          │
└──────────────────────────────┘
```

---

# 27. 警告設定

```python
move_warning = True
```

GUIで、

```text
[✓] 今後この警告を表示しない
```

を選択した場合：

```python
move_warning = False
```

とする。

ただし、初期値は必ず：

```python
True
```

とする。

---

# 28. ファイル名衝突処理

保存先に同名ファイルが存在する場合：

### ケース1：完全一致

```text
SHA-256一致

→ SKIP
```

### ケース2：同名・内容違い

```text
IMG001.JPG
IMG001_001.JPG
IMG001_002.JPG
```

のように新しい名前を生成する。

---

# 29. ファイル名生成

```python
def generate_unique_name(path):
    ...
```

例：

```text
IMG001.JPG
```

が存在する場合：

```text
IMG001_001.JPG
```

さらに存在：

```text
IMG001_002.JPG
```

---

# 30. エラー処理

各ファイルは独立して処理する。

```text
写真1 → 成功
写真2 → 成功
写真3 → エラー
写真4 → 成功
```

写真3のエラーだけで全処理を停止しない。

ただし、以下は全体停止する。

```text
保存先へのアクセス不能
ディスク容量不足
設定ファイル破損
入力元が存在しない
```

---

# 31. ログレベル

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

通常実行：

```text
INFO
WARNING
ERROR
```

デバッグ：

```text
DEBUG
```

---

# 32. テスト設計

## Unit Test

### Scanner

* JPEGを取得できる
* 対象外拡張子を除外する
* サブディレクトリを検索する

### Metadata

* EXIF日時取得
* EXIFなし
* 不正EXIF
* ファイル日時fallback

### Duplicate

* 同一ファイル
* 異なるファイル
* サイズ違い
* 同名・内容違い

### FileOperator

* コピー
* 移動
* エラー
* 権限エラー

### Organizer

* 通常コピー
* 通常移動
* 重複スキップ
* 日付フォルダ作成
* エラー継続

---

# 33. 最重要テスト

以下のテストは必須とする。

### コピー

```text
Source:
IMG001.JPG

Destination:
なし

実行

結果:
Destinationにコピー
Sourceは存在
```

### 重複コピー

```text
Source:
IMG001.JPG

Destination:
同一SHA-256のIMG001.JPG

実行

結果:
コピーしない
Sourceは存在
Destinationも存在
```

### 移動

```text
Source:
IMG001.JPG

Destination:
なし

y

実行

結果:
Destinationに存在
Sourceから消える
```

### 移動キャンセル

```text
Move

Continue? [y/N]

n
```

結果：

```text
Source変更なし
Destination変更なし
```

---

# 34. データ保護テスト

以下をテストする。

```text
SDカードを読み取り専用状態にする
        ↓
コピー実行
        ↓
正常終了する
        ↓
SDカードのファイルが変更されていない
```

コピー処理については、SDカードへの書き込み処理を実装しない。

---

# 35. 配布設計

## Windows

```text
PhotoOrganizer.exe
```

GUIアプリとして単体起動可能にする。

## macOS

```text
PhotoOrganizer.app
```

## Linux

```text
photo-organizer
```

---

# 36. 設定ファイルの扱い

配布ファイル内にユーザー固有の`.env`を含めない。

初回起動時：

```text
設定ファイルなし
      ↓
初期設定画面
      ↓
ユーザーが設定
      ↓
設定保存
```

CUIの場合：

```bash
photo-organizer init
```

で生成する。

---

# 37. 推奨セキュリティ設計

以下を原則とする。

```text
COPY = 非破壊
MOVE = 破壊的操作
DELETE = 原則実装しない
```

つまり、

```text
通常運用
    ↓
COPY
    ↓
安全

必要な場合のみ
    ↓
MOVE
    ↓
確認

削除
    ↓
別機能として扱う
```

---

# 38. 最終処理イメージ

```text
             SD CARD
                │
                ▼
       ┌─────────────────┐
       │ Photo Scanner   │
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │ Metadata Reader │
       └────────┬────────┘
                │
                ▼
          撮影日時取得
                │
                ▼
       ┌─────────────────┐
       │ Destination      │
       │ Resolver         │
       └────────┬────────┘
                │
                ▼
          yyyy/mm/dd
                │
                ▼
       ┌─────────────────┐
       │ Duplicate Check │
       └────────┬────────┘
                │
         ┌──────┴──────┐
         │             │
       DUPLICATE      NEW
         │             │
         ▼             ▼
       SKIP       COPY / MOVE
                       │
                       ▼
                 保存先フォルダ
```

---

# 39. 今後の拡張候補

初期バージョンでは実装せず、設計上拡張可能とする。

```text
V1.0
├── CUI
├── GUI
├── COPY
├── MOVE
├── EXIF
├── yyyy/mm/dd
└── SHA-256重複判定

V1.1
├── ドライラン
├── 詳細ログ
└── 処理結果CSV

V1.2
├── RAW
├── 動画
└── HEIC

V2.0
├── SDカード自動検出
├── 自動整理
├── フォルダ監視
└── バックアップ

V3.0
├── カメラ別整理
├── GPS整理
├── AI分類
└── 写真管理DB
```

# 40. 設計上の重要事項

本システムでは、**「写真を整理すること」よりも「元データを壊さないこと」を優先する。**

そのため、初期状態は必ず、

```text
COPY
```

とする。

また、

```text
完全同一データ
```

を検出しても、元ファイルを自動削除しない。

削除はコピー・移動とは別の操作として扱い、将来実装する場合も明示的なユーザー操作を要求する。

これにより、

```text
SDカード
   ↓
写真読み取り
   ↓
メタデータ取得
   ↓
日付判定
   ↓
重複判定
   ↓
保存
```

という安全な一方向処理を基本アーキテクチャとする。
