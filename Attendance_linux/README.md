# 勤怠管理システム自動入力ツール（Linux版）

SalesforceのSSOログインを開始し、Microsoftの保存済みアカウントを選択して、
勤務表画面を表示した後、当日の通常勤務時間を入力するSeleniumツールです。
本リポジトリは Windows 版（`Attendance`）を Linux サーバー（Ubuntu 26.04）での
cron 自動実行向けに移植したものです。

通常勤務日は出勤 `09:00`、退勤 `17:45` を入力する。休日には入力せず、
定時外の値が既にある場合は残業等の手動調整として上書きしない。
あわせて勤務場所を「出社」、業務内容を「開発業務」として日別行を保存する。
任意でJSONから既存ジョブの工数を読み込み、実労働時間との一致を確認して
保存できる。月次申請は既定で確認モードとし、未取得の確定画面を推測操作しない。

## 現在できること

### ログインと画面検出

- SalesforceのSSOログインを開始する
- Microsoftの保存済み対象アカウントを選択する
- Salesforce勤務表の表示完了を確認する
- 通常DOM、open Shadow DOM、iframeを横断して勤務表を検出する
- 認証タイムアウト、ネットワーク障害、画面要素変更を検出する

### 勤務情報の入力

- 通常勤務日の出勤・退勤時刻を入力して保存する
- 既定値として出勤`09:00`、退勤`17:45`を使用する
- 勤務時間入力ダイアログの対象日を再確認する
- 保存後に当日行を再取得し、出退勤時刻を確認する
- 勤務場所と業務内容を入力して保存する
- 既定値として勤務場所「出社」、業務内容「開発業務」を使用する
- 休日は勤務情報を入力しない
- 定時外の時刻を残業等の手動調整として保護する
- 同じ値が設定済みの場合は再保存しない

### 工数入力

- JSONから対象日のジョブコードと工数を読み込む
- 複数ジョブ、重複ジョブ、不正な時刻形式を検証する
- 工数合計と画面上の実労働時間を照合する
- 設定した許容差の範囲内で一致を判定する
- 工数入力ダイアログの対象日を再確認する
- 画面に存在するジョブの工数を入力して保存する
- 同じ工数が設定済みの場合は再保存しない
- 明示的に許可されていない既存工数の上書きを防止する
- 画面に存在しないジョブは推測追加せず安全に停止する

工数JSONの例:

```json
{
  "2026-07-31": [
    {
      "job_code": "JOB_SGY_44872243_01_01",
      "time": "07:45"
    }
  ]
}
```

### 日次勤務時間変更申請

`DAILY_REQUEST_ENABLED=true`の場合、勤務情報の保存後に次の順序で処理する。

1. 勤務時間入力ダイアログで対象日と申請状態を確認する。
2. ダイアログ上部の「申請」をクリックする。
3. 勤務表と対象日行を再取得する。
4. 対象日行内の申請ボタンをクリックする。
5. 申請画面の対象日を確認する。
6. 「勤務時間変更」をクリックする。
7. 未申請の場合だけ「申請」をクリックする。

「申請中」「承認済」「申請済み」または「取消し」が表示されている場合は
再申請しない。`--dry-run`では申請関連ボタンをクリックしない。

### 月次申請の確認

- 月次ステータスを読み取る
- 未申請、申請済み、差戻し系の状態を判定する
- 申請中、承認済、確定済の場合は再申請しない
- 差戻し、却下、取消の場合は自動再申請せずエラー通知する
- 確認モードでは月次勤務確定をクリックしない
- 未照合の確認画面に到達する操作は安全に停止する

### 安全制御と運用

- `--login-only`によるログイン・表示確認
- `--dry-run`による変更前の対象判定
- `--workload-only`による工数処理だけの実行
- `--check-config`による設定検証
- Chromeプロファイル単位の多重起動防止
- Salesforceへの主要操作を既定5秒間隔に制御（環境変数で変更可能）
- 分類済み終了コードによる実行結果判定
- エラー発生時のWebhook通知
- ログの日次ローテーションと保管日数指定
- アカウント、Cookie、認証トークン、Webhook URLのログ出力防止

## 現在できないこと

- 画面に存在しない新規ジョブの自動追加
- 工数保存後の実機再表示による完全な保存値検証
- 休暇、遅刻、早退申請の自動作成
- 差戻し内容の自動修正と再申請
- 月次勤務確定の自動送信
- 未取得画面に対する推測操作
- Windows Helloの自動操作
- MicrosoftパスワードやPINの自動入力

## セットアップ

```bash
cd /path/to/Attendance_linux
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env
```

> **proxy について**: このツールは**プロキシなし・インターネット直結の個人
> サーバーを前提**としており、一般的には `HTTP_PROXY` 等の設定は不要。
> もし proxy 環境（家庭の回線制限や VPN 等）で pip の selenium 導入や初回
> chromedriver 自動取得が失敗する場合は、[Linuxセットアップガイド](docs/linux_setup_guide.md)
> の「proxy を設定する場合」を参照すること。なお**実行時の Salesforce 通信**は
> Chromeが直接行うため、proxy が無くても動く。

`.env` を開いて `TARGET_ACCOUNT` などの各値を実環境に合わせて修正する。
`.env` は `config.py` が実行時に自動読込する（既存の環境変数がある場合は
`.env` を上書きしない）。通常利用中のChromeプロファイルではなく、
自動化専用プロファイル（`.env` の `CHROME_USER_DATA_DIR`）を指定する。
サーバー負荷を抑える操作間隔は `SERVER_REQUEST_DELAY_SECONDS` で指定し、
既定値は5秒、設定範囲は0～300秒である。

工数JSONの形式は
[サンプル](docs/workload.example.json)を参照する。保存済み画面に存在しない
ジョブは自動追加せず停止する。

設定項目の一覧と詳細は [Linuxセットアップガイド](docs/linux_setup_guide.md) を参照。
導入可否の判断、GUI認証、cron運用、セキュリティ、障害対応については
[Ubuntu 26.04 Server 導入・運用Q&A](docs/ubuntu_server_qa.md) を参照。

設計・利用資料（Windows版から継承）:

- [概要説明書](docs/overview.md)
- [基本設計書](docs/basic_design.md)
- [詳細設計書](docs/detailed_design.md)
- [ユーザーマニュアル・Q&A](docs/user_manual.md)

## 初回セッション確立（GUIログイン）

cron による自動実行はヘッドレスブラウザで行う。そのため事前に
GUI 環境でログインを1回成功させ、Chromeプロファイルにセッションを
保存しておく必要がある。

```bash
# .env の HEADLESS を false に変更する
sed -i 's/^HEADLESS=.*/HEADLESS=false/' .env

# GUI 環境でログインのみ実行する
.venv/bin/attendance-login --login-only
```

Microsoftアカウント選択・Hello/パスワードの手動操作でログインを成功させる。
ログインに成功して勤務表が表示されたら、ブラウザを閉じて完了。

```bash
# 確認後、自動実行用に HEADLESS を true へ戻す
sed -i 's/^HEADLESS=.*/HEADLESS=true/' .env
```

セッション期限切れ時も同じ手順で再ログインする。

## cron 登録

平日17:00に自動実行する cron を登録する。

```bash
# 登録（DRY_RUN=1 で確認だけの場合）
DRY_RUN=1 ./scripts/install_cron.sh

# 実際に登録
./scripts/install_cron.sh
```

登録内容は `0 17 * * 1-5`（平日17:00）で、実行ログはプロジェクトルートの
`cron.log` に追記される。エラー時の通知は cron メールではなく、`.env` の
`WEBHOOK_URL` への Webhook 通知で行う（未設定の場合は通知されない）。

確認と削除:

```bash
crontab -l                                   # 確認
crontab -e                                   # 削除・編集
```

## 実行

```bash
# 設定検証
.venv/bin/attendance-login --check-config

# ログイン・勤務表表示確認だけ
.venv/bin/attendance-login --login-only

# 変更を加えず対象判定だけ
.venv/bin/attendance-login --dry-run

# 実実行（平日17:00に cron から実行される）
.venv/bin/attendance-login
```

`--login-only` は勤務表の表示確認だけを行う。`--dry-run` は当日行を確認するが、
値の入力と保存は行わない。通常の `attendance-login` は実データを更新する。
`--workload-only` は勤務時間・勤務場所を変更せず、工数処理だけを行う。

cron 経由で実行する場合は `scripts/run_attendance_login.sh` を使う
（`.env` 自動読込のため環境変数の export は不要）。

```bash
./scripts/run_attendance_login.sh --check-config
```

または次の形式でも実行できる。

```bash
.venv/bin/python -m attendance_login.main
```

## メンテナンス

- **セッション期限切れ**: ヘッドレス実行が認証タイムアウトで失敗したら、
  GUI 環境で `HEADLESS=false` にして `--login-only` を再実行する。
- **ログファイル**: 実行ログは `~/.attendance-chrome/attendance-login.log`
  （`.env` の `LOG_FILE`）に出力される。cron 実行時の標準出力は
  `cron.log` に追記される。
- **多重起動**: Chromeプロファイル単位で多重起動を防止している。

## 終了コード

| コード | 意味 |
| ---: | --- |
| 0 | ログイン成功、勤務情報入力または安全なスキップ |
| 2 | 設定不備 |
| 3 | Chrome起動失敗（または実行ファイル不足） |
| 4 | 認証タイムアウト |
| 5 | 画面要素変更または対象アカウントなし |
| 6 | ネットワーク障害 |
| 7 | Webhook通知失敗 |
| 9 | 未分類エラー |

## セキュリティ

- パスワード、PIN、Cookieは設定・ログへ出力しない。
- Microsoftアカウント（`TARGET_ACCOUNT`）はログへ出力しない。
- Windows Hello / パスワードは自動操作せず、タイムアウト時に手動対応を通知する。
- `use_html` には保存時点の認証情報が含まれる可能性があるため外部公開しない。
- `.gitignore` で `.env`、`use_html`、仮想環境を除外している。
- `.env` のファイルパーミッションは所有者のみ読み書き（`chmod 600 .env`）を推奨する。
# 2026-attendance_linux
