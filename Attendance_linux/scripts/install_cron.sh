#!/bin/bash
# ============================================================
# 平日 17:00 実行の cron 登録スクリプト（Linux）
#
# 登録内容:
#   0 17 * * 1-5 cd <プロジェクトルート> && <プロジェクトルート>/scripts/run_attendance_login.sh >> <プロジェクトルート>/cron.log 2>&1
#
# - 既に登録されている場合は中断する（重複登録防止）
# - DRY_RUN=1 で実行すると登録予定の行を表示するだけ
# ============================================================
set -euo pipefail

# プロジェクトルートをこのスクリプトの場所から解決する
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 重複登録防止用のマーカー
MARKER="# AttendanceLinux"

# 登録する cron 行
CRON_LINE="0 17 * * 1-5 cd ${PROJECT_ROOT} && ${PROJECT_ROOT}/scripts/run_attendance_login.sh >> ${PROJECT_ROOT}/cron.log 2>&1"

# 既存の crontab を取得する（crontab が存在しなければ空とする）
if CURRENT="$(crontab -l 2>/dev/null)"; then
    :
else
    CURRENT=""
fi

# 既に登録済みなら終了する
if printf '%s\n' "${CURRENT}" | grep -qF "${MARKER}"; then
    echo "[install_cron] 既に登録済みです（${MARKER}）。確認: crontab -l"
    exit 0
fi

# 登録予定の内容を表示する
echo "[install_cron] 以下の cron を登録します:"
echo "  ${MARKER}  # 勤怠自動入力（AttendanceLinux）"
echo "  ${CRON_LINE}"
echo ""
echo "[install_cron] 注意: MAILTO は設定していません。"
echo "[install_cron] エラー時は cron メールの代わりに .env の WEBHOOK_URL へ Webhook 通知が送信されます。"
echo "[install_cron] 必要であれば WEBHOOK_URL を設定してください。"

# DRY_RUN の場合は反映せず終了する
if [ "${DRY_RUN:-0}" = "1" ]; then
    echo "[install_cron] DRY_RUN のため反映しませんでした。"
    exit 0
fi

# 既存の内容にマーカーと cron 行を追記して反映する
{
    printf '%s\n' "${CURRENT}"
    printf '%s\n' "${MARKER}  # 勤怠自動入力（AttendanceLinux）"
    printf '%s\n' "${CRON_LINE}"
} | crontab -

echo "[install_cron] cron を登録しました。確認: crontab -l"
