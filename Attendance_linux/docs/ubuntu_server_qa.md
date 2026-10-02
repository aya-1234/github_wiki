# Ubuntu 26.04 Server 導入・運用Q&A

この文書は、`attendance-login`をUbuntu 26.04 Serverへ導入し、cronで運用する際の判断事項と代表的なトラブルへの対処をまとめたものです。具体的なコマンドは[Linuxセットアップガイド](linux_setup_guide.md)も参照してください。

## 1. 導入前の確認

### Q1. Ubuntu 26.04 Serverで動作しますか？

アプリのパッケージ定義はPython 3.10以上を要求しており、Ubuntu 26.04.1 LTSのPython 3.14系はその範囲内です。Google Chromeも公式要件では64bit Ubuntu 18.04以降を対象としています。

ただし、Python 3.14、実際のMicrosoft認証、Salesforce勤務表を組み合わせた動作は、導入先で確認する必要があります。本稼働前に`--check-config`、`--login-only`、`--dry-run`の順で確認してください。

参考:

- [Ubuntu 26.04.1 LTS 公式配布ページ](https://releases.ubuntu.com/26.04/)
- [Ubuntu 26.04.1 Serverパッケージ一覧](https://releases.ubuntu.com/26.04/ubuntu-26.04.1-live-server-amd64.manifest)
- [Google Chromeのシステム要件](https://support.google.com/chrome/answer/95346)

### Q2. どのCPUアーキテクチャを利用できますか？

既存のChrome導入コマンドはAMD64（x86-64）用です。最初に次のコマンドで確認してください。

```bash
dpkg --print-architecture
```

`amd64`ならセットアップガイドのコマンドを利用できます。`arm64`の場合、アプリ自体は純Pythonですが、Chromeのarm64版パッケージを公式サイトから選び、導入先でSeleniumを含む一連の動作を別途検証してください。

### Q3. 必要なソフトウェアは何ですか？

主に次のものが必要です。

- Ubuntu 26.04 Server
- Python 3、`python3-venv`、`pip`
- Google Chrome Stable
- cron
- 初回認証時に操作できるGUIセッション
- PyPI、Chrome配布サイト、Microsoft認証、Salesforce、任意のWebhook通知先へのHTTPS通信

確認例:

```bash
python3 --version
google-chrome --version
systemctl is-active cron
timedatectl
```

### Q4. CPUやメモリはどの程度必要ですか？

固定の最低値は定めていません。処理の中心はChromeであり、同時実行数、ページ内容、サーバー上の他プロセスによって必要量が変わります。導入時にメモリ不足や`/dev/shm`不足が発生しないことを監視し、1ジョブずつ実行してください。

### Q5. rootで動かす必要はありますか？

ありません。Chromeと認証プロファイルをrootで常用しないでください。専用の一般ユーザーで仮想環境、`.env`、Chromeプロファイル、ログ、cronを一貫して管理します。パッケージ導入などOS管理操作だけに`sudo`を使います。

## 2. GUIと認証

### Q6. Ubuntu ServerにはGUIがありませんが運用できますか？

定常運用は`HEADLESS=true`で行えます。ただし、初回ログインとセッション失効後の再ログインには、対象サーバー上のChromeを人が操作できるGUIセッションが必要です。Ubuntu ServerイメージにはGUIが含まれないため、事前に次のいずれかを用意します。

- 管理コンソールや一時的なデスクトップ環境
- 組織で承認されたリモートデスクトップ方式
- 表示転送を含む、Chromeを対話操作できる管理経路

GUIの公開範囲、ファイアウォール、認証方式はサーバー管理方針に従ってください。認証後に不要となった一時GUIは停止または削除します。

### Q7. 初回ログインはどう行いますか？

`.env`の`HEADLESS=false`にして、GUIセッション内で次を実行します。

```bash
.venv/bin/attendance-login --login-only
```

Microsoftアカウント選択、パスワード、PIN、MFAなどは手動で完了させます。勤務表が表示されたらChromeを閉じ、`HEADLESS=true`へ戻します。その後、同じOSユーザーで`--login-only`を再実行してヘッドレスログインを確認します。

### Q8. 別のPCで作ったChromeプロファイルをコピーできますか？

推奨しません。Cookieや認証情報がOSの資格情報管理と結び付いている場合があり、動作しない可能性があります。また、プロファイル自体が機密情報です。原則として、cronを実行するユーザーが対象サーバー上で専用プロファイルを作成してください。

### Q9. パスワードやMFAを自動入力できますか？

できません。Microsoftのパスワード、PIN、Windows Hello、MFAは自動操作の対象外です。保存済みセッションが失効した場合は、管理者がGUIで再ログインします。

### Q10. 普段使っているChromeプロファイルを共用できますか？

共用しないでください。`CHROME_USER_DATA_DIR`には自動化専用ディレクトリを指定します。同じプロファイルを手動Chromeとcronが同時に利用すると、Chrome起動失敗やプロファイル破損の原因になります。

## 3. インストールと設定

### Q11. 基本的なインストール手順は？

```bash
sudo apt update
sudo apt install -y python3-venv cron curl wget

cd /path/to/Attendance_linux
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .
cp .env.example .env
chmod 600 .env
```

Chromeの導入と`.env`の各項目は[Linuxセットアップガイド](linux_setup_guide.md)に従ってください。

### Q12. 最低限変更する設定は？

少なくとも次を確認します。

- `TARGET_ACCOUNT`: Microsoftアカウント選択画面で使う対象
- `CHROME_USER_DATA_DIR`: 自動化専用プロファイル
- `HEADLESS`: 初回認証時は`false`、cron運用時は`true`
- `WORK_START_TIME`、`WORK_END_TIME`: 定時
- `WORK_PLACE`、`BUSINESS_CONTENT`: 日次入力内容
- `WEBHOOK_URL`: 障害通知が必要なら設定

工数、日次変更申請、月次申請は既定で無効です。必要性と安全性を確認してから個別に有効化してください。

### Q13. `.env`はどの権限にすべきですか？

所有者だけが読み書きできるようにします。

```bash
chmod 600 .env
stat -c '%a %U:%G %n' .env
```

期待する権限は`600`です。`.env`をGitへ追加したり、チャットやチケットへそのまま貼り付けたりしないでください。

### Q14. Chromeプロファイルや工数JSONの権限は？

cronを実行する専用ユーザーだけがアクセスできる状態にします。

```bash
chmod 700 "$HOME/attendance-chrome"
chmod 600 "$HOME/attendance-workload.json"
```

工数入力を使わない場合、工数JSONは不要です。バックアップにも認証Cookieが含まれ得るため、Chromeプロファイルは暗号化して保管し、アクセスを限定してください。

### Q15. Webhookは必須ですか？

必須ではありません。`WEBHOOK_URL`が空なら通知は送信されません。ただしcronメールも設定していないため、無通知のまま障害が継続する可能性があります。本番運用ではWebhookまたは別のログ監視を用意してください。

### Q16. proxyは必要ですか？

インターネットへ直接接続できる環境では不要です。proxy環境では、pipやSelenium Managerだけでなく、ChromeからMicrosoft認証とSalesforceへ接続できることを確認してください。cronはログインシェルの環境変数を通常継承しないため、対話実行だけ成功する場合はcron側の環境を確認します。

## 4. cronと時刻

### Q17. cronはどのユーザーへ登録しますか？

セットアップ、初回認証、Chromeプロファイル作成を行った専用ユーザーへ登録します。そのユーザーで次を実行してください。

```bash
DRY_RUN=1 ./scripts/install_cron.sh
./scripts/install_cron.sh
crontab -l
```

rootのcrontabへ登録すると、別のホームディレクトリや別のChromeプロファイルが使われるため避けてください。

### Q18. 何時に実行されますか？

登録スクリプトの既定値は、平日の17:00です。

```text
0 17 * * 1-5
```

cronの時刻はサーバーのローカルタイムゾーンに従います。日本時間で実行するサーバーは次を確認してください。

```bash
timedatectl
```

必要なら管理者が次のように変更します。

```bash
sudo timedatectl set-timezone Asia/Tokyo
```

アプリが勤務表から探す「当日」は日本標準時で判定しますが、cronの起動時刻はOS設定に依存する点に注意してください。

### Q19. 土日や祝日にも入力されますか？

cronは月曜日から金曜日だけ起動します。日本の祝日はcron自体では除外しませんが、アプリは勤務表上の当日行が勤務日でない場合、勤務情報を入力せず安全に終了します。会社独自休日も勤務表上の区分に従います。

### Q20. cronと手動実行が重なった場合は？

Chromeプロファイル単位のロックにより、後から開始した処理は終了コード3で失敗します。手動確認はcronの時刻を避けて実施してください。ロックを回避するために別プロファイルを安易に指定すると、同じ勤務データを並行更新する危険があります。

## 5. 本稼働前の確認

### Q21. どの順番で確認すれば安全ですか？

次の順番を推奨します。

```bash
# 1. 設定とファイルパスだけを検証
.venv/bin/attendance-login --check-config

# 2. ログインと勤務表表示だけを確認
.venv/bin/attendance-login --login-only

# 3. 保存せず、当日の処理対象だけを確認
.venv/bin/attendance-login --dry-run

# 4. cronと同じラッパーから設定を検証
./scripts/run_attendance_login.sh --check-config
```

ログと勤務表の対象日を確認した後に通常実行し、最後にcronを登録します。

### Q22. `--dry-run`なら完全に外部通信しませんか？

いいえ。ログインと勤務表の読み取りには外部通信します。`--dry-run`が防ぐのは、勤務情報の入力・保存、申請関連ボタンのクリックです。

### Q23. 正常終了をどう判断しますか？

終了コード0とログを確認します。終了コード0には、保存成功だけでなく、休日、設定済み、手動調整値を保護した安全なスキップも含まれます。必要に応じて勤務表画面でも結果を確認してください。

## 6. セキュリティと運用

### Q24. サーバー上で特に保護すべきものは？

次を機密情報として扱います。

- `.env`
- `CHROME_USER_DATA_DIR`以下のChromeプロファイル
- 工数JSON
- `use_html`以下の保存HTML
- Webhook URL
- 実行ログと`cron.log`

ログにはアカウントやトークンを意図的に出さない実装ですが、障害調査情報やアクセス先が含まれる可能性があります。必要な管理者だけが読める権限にしてください。

### Q25. 外部へ公開するポートは必要ですか？

定常的なヘッドレス実行だけなら、このアプリ専用の待受ポートは不要です。外向きHTTPS通信が必要です。初回認証用にリモートGUIを用意する場合だけ、その方式に必要な通信を管理ネットワークへ限定してください。

### Q26. バックアップ対象は何ですか？

再構築可能なソースコードや`.venv`より、環境固有の設定を優先します。

- `.env`（暗号化して保管）
- 工数JSON（利用時）
- cron設定の控え

Chromeプロファイルのバックアップは機密性が高く、復元後も認証が有効とは限りません。復旧手順は「アプリを再配置し、`.env`を復元し、GUIで再ログインする」ことを基本にします。

### Q27. OSやChromeを更新してもよいですか？

セキュリティ更新は適用してください。ただしChrome更新後はSelenium Managerが対応するdriverを取得する場合があります。更新後に`--login-only`と`--dry-run`を行い、勤務表の画面変更も含めて確認してから本実行します。

### Q28. アプリを停止または撤去するには？

まず`crontab -e`で`# AttendanceLinux`と直下の実行行を削除します。撤去時は、組織の保持方針に従って`.env`、工数JSON、ログ、Chromeプロファイルを安全に削除してください。Chromeプロファイルを削除すると保存済みセッションは復元できません。

## 7. トラブルシューティング

### Q29. 終了コードの意味は？

| コード | 意味 | 最初に確認すること |
|---:|---|---|
| 0 | 成功または安全なスキップ | ログで保存／スキップ理由を確認 |
| 2 | 設定不備 | `.env`、必須値、パス、値の範囲 |
| 3 | Chrome起動失敗または多重起動 | Chrome、プロファイル、残存プロセス、ロック競合 |
| 4 | 認証タイムアウト | セッション失効、MFA待ち、タイムアウト値 |
| 5 | 画面要素変更または対象アカウントなし | Salesforce／Microsoft画面、対象アカウント |
| 6 | ネットワーク障害 | DNS、HTTPS疎通、proxy、ページ読込時間 |
| 7 | Webhook通知失敗 | 通知先URL、認証、到達性 |
| 9 | 未分類エラー | ログと直前の更新内容 |

### Q30. 認証タイムアウトが発生しました。

保存済みセッションの失効を最初に疑います。GUIで`HEADLESS=false`にして`--login-only`を実行し、手動認証後に`HEADLESS=true`へ戻します。単に画面表示が遅い場合だけ`LOGIN_TIMEOUT_SECONDS`を増やしてください。

### Q31. Chromeが起動しません。

次を確認します。

```bash
google-chrome --version
ps aux | grep -i '[c]hrome'
df -h
df -h /dev/shm
ls -ld "$HOME/attendance-chrome"
```

同じプロファイルを使うChromeが残っていれば、その処理の終了を確認します。Chromeとdriverの不整合が疑われる場合は、キャッシュ削除の前にログとChromeバージョンを記録し、[Linuxセットアップガイド](linux_setup_guide.md)の手順を参照してください。

### Q32. 手動実行は成功するのにcronでは失敗します。

次の違いを確認します。

- cronを登録したOSユーザー
- `HOME`とファイルの所有者・権限
- カレントディレクトリ
- proxyなどの環境変数
- サーバーのタイムゾーン
- `.venv/bin/attendance-login`の存在

まずcronと同じラッパーを対話的に実行します。

```bash
./scripts/run_attendance_login.sh --check-config
./scripts/run_attendance_login.sh --dry-run
```

### Q33. Webhook通知が届きません。

`WEBHOOK_URL`が空なら通知されません。URLの有効性、HTTPS到達性、通知先の認証トークンを確認してください。なお、元の処理エラーに加えてWebhook送信も失敗すると終了コード7になります。根本原因は通知エラーより前のログも確認します。

### Q34. 画面要素変更エラーが発生しました。

自動再試行で保存を繰り返さず、まず`--login-only`または`--dry-run`で再現を確認します。MicrosoftやSalesforceの画面構造が変わった可能性があるため、ログの画面状態とURLのホスト・パスを確認し、セレクター修正が必要ならコード変更として扱います。認証情報を含み得る画面HTMLやスクリーンショットは外部公開しないでください。

### Q35. ログはどこにありますか？

既定のアプリログは`~/attendance-chrome/attendance-login.log`、cronの標準出力・標準エラーはプロジェクトルートの`cron.log`です。アプリログは日次ローテーションされ、既定で30日保持されます。`cron.log`には自動ローテーションがないため、長期運用ではlogrotateなどを別途設定してください。

## 8. 現在の制限

### Q36. 完全無人で永続運用できますか？

できません。Microsoftセッションの失効時には人による再認証が必要です。また、認証画面やSalesforce勤務表のDOM変更時にはコード修正が必要になる場合があります。通知と定期的なログ確認を前提にしてください。

### Q37. 月次申請まで自動送信できますか？

現在は安全上、未照合の確定画面を推測操作しません。月次ステータスの確認はできますが、自動送信は停止する実装です。日次勤務時間変更申請は個別設定で有効化できますが、本稼働前に`--dry-run`で対象を確認してください。

### Q38. 休暇、遅刻、早退や新しい工数ジョブを自動登録できますか？

できません。休暇・遅刻・早退申請、画面に存在しない新規ジョブの追加、差戻し内容の自動修正は対象外です。これらは手動で対応してください。
