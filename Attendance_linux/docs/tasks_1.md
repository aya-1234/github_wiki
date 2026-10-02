# サーバー操作間隔制御 タスク一覧（tasks_1.md）

> 本ファイルは初回タスク一覧のため前ファイルは存在しない。
> 本ファイルは大目標1個を管理する。完了後の新規変更は `tasks_2.md` から再開する。

> `docs/server_request_delay_design.md` に基づき、実装・テスト・確認を進めるためのタスク一覧である。

| 項目 | 内容 |
|---|---|
| 文書種別 | タスク一覧（進捗管理・複数ファイル方式） |
| 元設計書 | `docs/server_request_delay_design.md` |
| 前ファイル | なし |
| 次ファイル | `docs/tasks_2.md`（次の変更時に作成） |
| 作成日 | 2026-09-17 |
| 状態管理 | 下表の「状態」列を更新する |

## 状態凡例

- `未着手` … まだ手を付けていない
- `実施中` … 作業中
- `完了` … 実装・テスト・確認が終了

## 1. 機能実装タスク

### 1.1 サーバー操作間隔制御（設計書 §3）

| ID | タスク内容 | 設計書節 | 状態 | 備考 |
|---|---|---|---|---|
| TASK-01 | 設定値と共通レート制御を実装する | §3.2 | 完了 | 既定5秒、0～300秒 |
| TASK-02 | ログイン・勤務情報・工数・日次申請へ共有制御を適用する | §3.2 | 完了 | 主要なサーバー操作が対象 |
| TASK-03 | 設定例と利用ドキュメントを更新する | §3.1～3.3 | 完了 | `.env`と`.env.example`を含む |

## 2. テストタスク

### 2.1 単体テスト（設計書 §3.5）

| ID | テストID | テスト内容 | 期待結果 | 状態 | 備考 |
|---|---|---|---|---|---|
| TASK-04 | UT-001 | レート制御の初回・残り時間・経過済み・0秒を検証する | 必要な場合だけ待機する | 完了 | 時刻をモック化 |
| TASK-05 | UT-002 | 設定値の既定・境界・不正値を検証する | 既定5秒、範囲外は設定エラー | 完了 | 環境変数テスト |

### 2.2 結合テスト（設計書 §3.5）

| ID | テスト内容 | 期待結果 | 状態 | 備考 |
|---|---|---|---|---|
| TASK-06 | `main.run` から各処理へのレート制御引き渡しを確認する | 同一インスタンスが共有される | 完了 | モック検証 |

### 2.3 手動確認（設計書 §3.5）

| ID | 確認内容 | 環境 | 状態 | 備考 |
|---|---|---|---|---|
| TASK-07 | `--check-config` で既定設定を検証する | ローカル仮想環境 | 完了 | ログ先のみ`/tmp`へ一時上書き、外部アクセスなし |

## 3. 非機能・検証タスク

| ID | 内容 | 状態 | 備考 |
|---|---|---|---|
| TASK-08 | 全テストによる非退行確認 | 完了 | pytest未導入のためunittestで全92件成功 |
| TASK-09 | パッケージビルドまたは同等の構文・配布検証 | 完了 | compileall成功、wheel生成成功 |

## 4. 完了条件の確認

| 完了条件 | 対応タスク | 判定 |
|---|---|---|
| サーバー操作が既定で最低5秒間隔になる | TASK-01, TASK-02, TASK-04, TASK-06 | 適合 |
| 環境変数で0～300秒に変更できる | TASK-01, TASK-03, TASK-05 | 適合 |
| 既存機能が退行しない | TASK-08, TASK-09 | 適合 |
| 設定検証が成功する | TASK-07 | 適合 |
| 本ファイル内の全大目標が完了 | TASK-01～TASK-09 | 完了 |

> 完了後の新規変更は `docs/tasks_2.md` から再開する。

## 5. 優先順位と推奨実施順

1. TASK-01、TASK-02
2. TASK-04、TASK-05、TASK-06
3. TASK-03
4. TASK-07、TASK-08、TASK-09

## 6. 関連ファイル

| 種別 | パス |
|---|---|
| 設計書 | `docs/server_request_delay_design.md` |
| 実装 | `attendance_login/pacing.py`、`attendance_login/config.py`、各操作モジュール |
| テスト | `tests/test_pacing.py`、`tests/test_config.py`、`tests/test_main.py` |
| 前ファイル | なし |
| 次ファイル | `docs/tasks_2.md`（次の変更時に作成） |

## 7. 検証結果

- `.venv/bin/python -m unittest discover -s tests -v`: 92件成功
- `.venv/bin/python -m compileall -q attendance_login tests`: 成功
- `env LOG_FILE=/tmp/attendance-login-check.log .venv/bin/attendance-login --check-config`: 成功
- `python3 -m pip wheel --no-deps --no-build-isolation --wheel-dir /tmp/attendance-linux-wheel .`: 成功
- 生成物: `/tmp/attendance-linux-wheel/attendance_login-0.1.0-py3-none-any.whl`
- フィードバック: 現時点で追加修正事項なし。次の変更は `tasks_2.md` から管理する。
