"""CLIエントリーポイント。"""

from __future__ import annotations

import argparse
import logging
import sys

from selenium.common.exceptions import WebDriverException

from .browser import create_driver
from .application import confirm_monthly_application
from .config import Config
from .daily_request import submit_daily_work_time_request
from .errors import (
    AttendanceLoginError,
    ConfigurationError,
    NotificationError,
)
from .login import execute_login
from .logging_config import configure_logging
from .notifier import send_notification
from .instance_lock import profile_lock
from .pacing import RequestPacer
from .work_hours import enter_regular_work_hours, record_daily_details
from .work_hours import _today_in_japan
from .workload import WorkloadResult, enter_workload, load_workload

LOGGER = logging.getLogger(__name__)


def run(
    config: Config,
    *,
    login_only: bool = False,
    dry_run: bool = False,
    workload_only: bool = False,
) -> int:
    driver = None
    succeeded = False
    request_pacer = RequestPacer(config.server_request_delay_seconds)
    try:
        driver = create_driver(config)
        execute_login(driver, config, request_pacer=request_pacer)
        if not login_only and not workload_only:
            enter_regular_work_hours(
                driver,
                timeout=config.work_input_timeout,
                start_time=config.work_start_time,
                end_time=config.work_end_time,
                dry_run=dry_run,
                request_pacer=request_pacer,
            )
            record_daily_details(
                driver,
                timeout=config.work_input_timeout,
                work_place=config.work_place,
                business_content_value=config.business_content,
                dry_run=dry_run,
                request_pacer=request_pacer,
            )
            if config.daily_request_enabled:
                submit_daily_work_time_request(
                    driver,
                    timeout=config.work_input_timeout,
                    dry_run=dry_run,
                    request_pacer=request_pacer,
                )
        if not login_only and config.workload_enabled:
            if config.workload_file is None:
                raise ConfigurationError(
                    "工数入力が有効ですがWORKLOAD_FILEが未設定です"
                )
            entries = load_workload(
                config.workload_file, _today_in_japan()
            )
            workload_result = enter_workload(
                driver,
                entries,
                timeout=config.work_input_timeout,
                tolerance_minutes=config.workload_tolerance_minutes,
                allow_overwrite=config.workload_allow_overwrite,
                dry_run=dry_run,
                request_pacer=request_pacer,
            )
        else:
            workload_result = None
        application_ready = workload_result in {
            WorkloadResult.SAVED,
            WorkloadResult.WOULD_SAVE,
            WorkloadResult.ALREADY_SET,
        }
        if (
            not login_only
            and config.application_enabled
            and application_ready
        ):
            confirm_monthly_application(
                driver,
                confirm_only=(config.application_confirm_only or dry_run),
                auto_submit=config.application_auto_submit,
            )
        elif not login_only and config.application_enabled:
            LOGGER.warning(
                "工数が申請可能な状態ではないため月次申請を行いません"
            )
        succeeded = True
        return 0
    except AttendanceLoginError as exc:
        LOGGER.error("%s", exc)
        current_url = ""
        if driver is not None:
            try:
                current_url = driver.current_url
            except WebDriverException:
                pass
        try:
            send_notification(
                config.webhook_url,
                exc.event,
                str(exc),
                current_url,
                config.webhook_timeout,
            )
        except NotificationError as notification_error:
            LOGGER.error("%s", notification_error)
            return notification_error.exit_code
        return exc.exit_code
    except Exception as exc:
        # 秘密情報を含み得る例外詳細は通常ログへ展開しない。
        LOGGER.exception("想定外のエラーが発生しました")
        current_url = ""
        if driver is not None:
            try:
                current_url = driver.current_url
            except WebDriverException:
                pass
        try:
            send_notification(
                config.webhook_url,
                "UNEXPECTED_ERROR",
                f"想定外のエラーが発生しました: {type(exc).__name__}",
                current_url,
                config.webhook_timeout,
            )
        except NotificationError as notification_error:
            LOGGER.error("%s", notification_error)
            return notification_error.exit_code
        return 9
    finally:
        if driver is not None and (
            succeeded or not config.keep_browser_open_on_error
        ):
            try:
                driver.quit()
            except WebDriverException:
                LOGGER.warning("Chromeの終了処理に失敗しました")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Salesforce勤怠管理システムへログインし、"
            "当日の定時勤務時間を入力します"
        )
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="設定値の検証だけを行い、Chromeを起動しません",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--login-only",
        action="store_true",
        help="勤務表へのログイン確認だけを行い、勤務情報を変更しません",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="勤務情報の入力対象を確認し、値の入力や保存は行いません",
    )
    mode.add_argument(
        "--workload-only",
        action="store_true",
        help="勤務情報を変更せず、設定されている工数処理だけを行います",
    )
    return parser


def cli() -> int:
    args = build_parser().parse_args()
    try:
        config = Config.from_env()
        config.validate_runtime_paths()
    except ConfigurationError as exc:
        configure_logging("INFO")
        LOGGER.error("%s", exc)
        return exc.exit_code

    configure_logging(
        config.log_level,
        config.log_file,
        config.log_retention_days,
    )
    if args.check_config:
        LOGGER.info("設定値は有効です")
        return 0
    try:
        with profile_lock(config.user_data_dir):
            return run(
                config,
                login_only=args.login_only,
                dry_run=args.dry_run,
                workload_only=args.workload_only,
            )
    except AttendanceLoginError as exc:
        LOGGER.error("%s", exc)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(cli())
