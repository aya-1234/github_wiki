# Linux セットアップガイド（Attendance_linux）

Ubuntu 26.04 サーバーで `attendance-login` を cron 自動実行するための
セットアップ手順を説明する。**個人所有のサーバーで、プロキシなし・
インターネット直結** の環境を対象とする（企業ネットワークのような proxy 前提
の環境で利用する場合は、最後の「proxy を設定する場合」を参照）。

## 1. 前提条件

- Ubuntu 26.04（Python 3.14系）
- Google Chrome がインストール済み（未導入なら後述の手順で導入）
- cron デーモンが稼働中
- GUI セッションが1回だけ利用可能（初回セッション確立用）
- **プロキシ設定は不要**（インターネット直結のため）

インターネットへは直結できるため、`HTTP_PROXY` などの proxy 環境変数は
設定しなくてよい。`pip install` や Selenium Manager による chromedriver の
自動取得も proxy なしで完了する。

### ネットワーク疎通の確認

```bash
# 外へ出られるか確認（例: PyPI）
curl -I https://pypi.org/simple/ 2>&1 | head -5

# Google Chrome が入っているか
google-chrome --version
```

### Chrome の導入（未導入の場合）

```bash
# Ubuntu 26.04 / AMD64 の場合
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y ./google-chrome-stable_current_amd64.deb
```

### proxy を設定する場合（個人サーバーで必要になったら）

個人サーバーでは原則 proxy 不要。ただし自宅等でキャプティブポータルや
VPN・透過 proxy 環境に置く場合のみ、以下で対応する。

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1
```

cron 実行時には `.bashrc` の export が効かないため、`/etc/environment`
または crontab 冒頭にも設定する。なお **Salesforce 通信用に proxy は不要**。
proxy が必要になるのは chromedriver の初回ダウンロードや pip 等だけなので、
設定済みキャッシュがあれば実行は proxy なしでも動く。

## 2. 仮想環境の構築と依存インストール

```bash
cd /path/to/Attendance_linux
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .
```

`pip install -e .` の際、requirements.txt に含まれる selenium などが
インストールされる。selenium はインストール時に chromedriver を直接は
持たず、**初回ブラウザ起動時に Selenium Manager がインターネット（直結）
経由で chromedriver を自動取得**する。個人サーバーなら proxy なしで取得できる。

この取得に失敗する場合は、次のいずれかを行う。

```bash
# キャッシュを削除して再取得を試みる
rm -rf ~/.cache/selenium
# ネットワーク接続を再確認する
curl -I https://googlechromelabs.github.io/ 2>&1 | head -5
```

chromedriver は「Chromeのバージョンと一致」している必要がある。サーバーの
Chrome バージョンは以下で確認できる。

```bash
google-chrome --version
```

## 3. .env の作成と設定

```bash
cp .env.example .env
chmod 600 .env
```

`.env` は `config.py` が実行時に自動読込する（Python標準ライブラリのみで
実装しており、python-dotenv は不要）。既に os.environ に値がある場合は
その値が優先され、`.env` は上書きしない。

### 設定項目一覧

| キー | 既定値 | 説明 |
| --- | --- | --- |
| `ATTENDANCE_TOP_URL` | （二重エンコードURL） | 確定済み起点URL。変更しないこと。 |
| `CHROME_USER_DATA_DIR` | `~/attendance-chrome` | 自動化専用Chromeプロファイル置き場 |
| `CHROME_PROFILE_DIRECTORY` | `Default` | Chromeプロファイル名 |
| `TARGET_ACCOUNT` | （設定必須） | Microsoftアカウント選択画面の対象アカウント |
| `WEBHOOK_URL` | 空 | エラー通知先。空で通知無効 |
| `LOGIN_TIMEOUT_SECONDS` | `60` | ログインタイムアウト（秒） 1～300 |
| `PAGE_LOAD_TIMEOUT_SECONDS` | `30` | ページ読込タイムアウト（秒） 1～300 |
| `WEBHOOK_TIMEOUT_SECONDS` | `5` | Webhook送信タイムアウト（秒） 1～60 |
| `SERVER_REQUEST_DELAY_SECONDS` | `5` | Salesforceへの主要操作の最小間隔（秒） 0～300 |
| `HEADLESS` | `true` | ヘッドレス実行。cron運用は `true` |
| `KEEP_BROWSER_OPEN_ON_ERROR` | `false` | エラー時ブラウザ維持 |
| `LOG_LEVEL` | `INFO` | DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `LOG_FILE` | `~/attendance-chrome/attendance-login.log` | ログ出力先 |
| `LOG_RETENTION_DAYS` | `30` | ログ保持日数 1～365 |
| `WORK_START_TIME` | `09:00` | 出勤時刻（HH:MM 2桁） |
| `WORK_END_TIME` | `17:45` | 退勤時刻（HH:MM 2桁） |
| `WORK_PLACE` | `出社` | 勤務場所 |
| `BUSINESS_CONTENT` | `開発業務` | 業務内容（255文字以内） |
| `WORKLOAD_ENABLED` | `false` | 工数入力の有効化 |
| `WORKLOAD_FILE` | `~/attendance-workload.json` | 工数JSONの場所（有効時必須） |
| `WORKLOAD_ALLOW_OVERWRITE` | `false` | 既存工数の上書き許可 |
| `WORKLOAD_TOLERANCE_MINUTES` | `0` | 工数照合の許容差（分） 0～60 |
| `APPLICATION_ENABLED` | `false` | 勤務表申請の有効化 |
| `APPLICATION_CONFIRM_ONLY` | `true` | 申請時の確認モード |
| `APPLICATION_AUTO_SUBMIT` | `false` | 自動送信（安全上の注意あり） |
| `DAILY_REQUEST_ENABLED` | `false` | 日次勤務時間変更申請の有効化 |
| `WORK_INPUT_TIMEOUT_SECONDS` | `10` | 勤務時間入力のタイムアウト（秒） 1～120 |

`CHROME_USER_DATA_DIR` のディレクトリは最初のログイン時に自動生成される。
`WORKLOAD_FILE` を指定する場合は、実行前に JSON ファイルを配置しておくこと。
`SERVER_REQUEST_DELAY_SECONDS` は初回アクセス後のページ遷移・保存・申請などに
共通で適用される。サーバー負荷軽減のため、通常は既定の5秒以上を推奨する。
`0`を指定すると待機を無効化できる。

## 4. 初回GUIログインとヘッドレス運用の切替

cron からの自動実行は `HEADLESS=true`（ヘッドレス）で行う。ただしヘッドレス
では Microsoft アカウント・Hello/パスワードの操作を自動化できないため、
**初回のみ GUI 環境でログインを1回成功させ、Chromeプロファイルにセッションを
保存**しておく必要がある。

```bash
# 1) GUI モードに切り替える
sed -i 's/^HEADLESS=.*/HEADLESS=false/' .env

# 2) GUI でログインのみ実行（ブラウザが開く）
.venv/bin/attendance-login --login-only
```

Microsoftアカウント選択、Hello/パスワード入力は手動で行う。勤務表画面が
表示されてログイン成功が確認できたらブラウザを閉じる。

```bash
# 3) cron 運用のためにヘッドレスへ戻す
sed -i 's/^HEADLESS=.*/HEADLESS=true/' .env

# 4) 設定を確認する
.venv/bin/attendance-login --check-config
```

セッションが期限切れになった場合は、同じ手順（`HEADLESS=false` →
`--login-only` → `HEADLESS=true`）で再ログインする。

## 5. cron 登録・確認・削除

### 登録

```bash
cd /path/to/Attendance_linux

# 登録予定の内容を確認（反映しない）
DRY_RUN=1 ./scripts/install_cron.sh

# 登録する
./scripts/install_cron.sh
```

登録される内容（平日17:00）:

```
0 17 * * 1-5 cd /path/to/Attendance_linux && /path/to/Attendance_linux/scripts/run_attendance_login.sh >> /path/to/Attendance_linux/cron.log 2>&1
```

- マーカー `# AttendanceLinux` で重複登録を防止している。
- 実行ログはプロジェクトルートの `cron.log` に追記される。
- `MAILTO` は設定していない。エラー時の通知は `.env` の `WEBHOOK_URL` への
  Webhook 通知で行う（未設定の場合は通知されない点に注意）。

### 確認

```bash
crontab -l
```

### 削除・編集

```bash
crontab -e
```

マーカー `# AttendanceLinux` と、その直下の cron 行を削除する。

## 6. 動作確認

```bash
# 設定の検証
.venv/bin/attendance-login --check-config

# 対象判定のみ（実データを変更しない）
.venv/bin/attendance-login --dry-run

# 手動で1回だけ実行する
.venv/bin/attendance-login
```

cron 経由と同じ経路を試す場合:

```bash
./scripts/run_attendance_login.sh --check-config
```

## 7. トラブルシューティング

### 認証タイムアウト（終了コード 4）

- セッションが期限切れの可能性が高い。GUI 環境で `HEADLESS=false` にし、
  `--login-only` を実行して再ログインする。
- `LOGIN_TIMEOUT_SECONDS` を増やす（最大300秒）。

### セッション切れ（毎日失敗する）

- ログイン成功後のセッション有効期間に依存する。定期的に手動再ログインする
  運用が必要な場合は、カレンダーでリマインドするか、Webhook 通知の内容で
  検知する。

### Chrome 起動失敗（終了コード 3）

- `CHROME_USER_DATA_DIR` が存在するか確認する（初回は空でよい）。
- Chrome が 起動できるか直接確認する:
  ```bash
  google-chrome --version
  ```
- ヘッドレス実行で GPU 関連のエラーが出る場合は環境変数を追加して試す:
  ```bash
  CHROME_OPTS="--no-sandbox --disable-dev-shm-usage" .venv/bin/attendance-login
  ```
  （恒久対応は browser.py の起動引数に追加するが、既定実装では変更しない）
- chromedriver と Chrome のバージョン不一致が疑われる場合は
  `rm -rf ~/.cache/selenium` して再取得させる。

### ロック競合（多重起動）

- Chromeプロファイル単位の多重起動防止により、既に実行中なら2つ目は失敗する。
- cron 実行と手動実行が重ならないよう、実行時間帯をずらす。
- 以前のプロセスが残っている場合はプロセスを確認する:
  ```bash
  ps aux | grep -i chrom
  ```

### Webhook 通知がない

- `.env` の `WEBHOOK_URL` が設定されているか確認する（空なら通知無効）。
- 通知先への到達性（URL・トークンの有効性）を確認する。

### ネットワーク / proxy 関連のエラー

- **個人サーバー（直結）なのに chromedriver 取得や pip が失敗する**:
  その時点のネットワーク（DNS・外部疎通・認証ポータル等）を確認する。
  ```bash
  curl -I https://pypi.org/simple/ 2>&1 | head -5
  ```
- **proxy を設定している環境でエラーが出る**: `HTTP_PROXY` / `HTTPS_PROXY` /
  `NO_PROXY` が cron 実行時にも設定されているか確認する。cron はログイン
  シェルの環境変数を継承しないため、`/etc/environment` または crontab 冒頭の
  export で設定しておくのが確実。proxy を設定していないのにエラーが出る
  場合も、誤って proxy 環境変数が残っていないか確認する。

## 8. 参考

- 元の Windows 用スクリプト（参考資料）: `scripts/windows/`
- 設計・利用資料は README の「設計・利用資料」リンクを参照。
