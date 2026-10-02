#!/bin/bash
# ============================================================
# attendance-login 実行スクリプト（Linux / cron 用）
#
# - プロジェクトルートを解決して cd する
# - .venv の attendance-login コマンドを実行する
# - 環境変数は config.py の .env 自動読込に任せる（export 不要）
# - 引数はそのまま渡し、終了コードもそのまま返す
# ============================================================
set -euo pipefail

# プロジェクトルートをこのスクリプトの場所から解決する
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# 実行ファイルのパス
COMMAND="${PROJECT_ROOT}/.venv/bin/attendance-login"

# .venv が存在しなければエラーで終了する（終了コード 3）
if [ ! -x "${COMMAND}" ]; then
    echo "[run_attendance_login] エラー: ${COMMAND} が見つかりません。" >&2
    echo "[run_attendance_login] セットアップ手順: python3 -m venv .venv && .venv/bin/pip install -e ." >&2
    exit 3
fi

# 引数をそのまま渡して実行する。終了コードはそのまま返す。
"${COMMAND}" "$@"
exit $?
