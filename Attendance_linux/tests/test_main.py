from dataclasses import replace
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from attendance_login.config import Config
from attendance_login.errors import (
    BrowserStartupError,
    NetworkError,
    NotificationError,
    SelectorChangedError,
)
from attendance_login.main import run
from attendance_login.workload import WorkloadResult


def config() -> Config:
    return Config(
        top_url="https://example.com/",
        user_data_dir=Path("/tmp"),
        profile_directory=None,
        target_account="user@example.com",
        webhook_url="https://example.com/webhook",
        login_timeout=1,
        page_load_timeout=1,
        webhook_timeout=1,
        headless=False,
        keep_browser_open_on_error=False,
        log_level="INFO",
        log_file=None,
        log_retention_days=30,
        work_start_time="09:00",
        work_end_time="17:45",
        work_place="出社",
        business_content="開発業務",
        work_input_timeout=10,
    )


class MainExitCodeTest(TestCase):
    def test_browser_startup_error_returns_3(self) -> None:
        with (
            patch(
                "attendance_login.main.create_driver",
                side_effect=BrowserStartupError("起動失敗"),
            ),
            patch("attendance_login.main.send_notification") as notify,
        ):
            self.assertEqual(run(config()), 3)
        notify.assert_called_once()

    def test_notification_error_returns_7(self) -> None:
        with (
            patch(
                "attendance_login.main.create_driver",
                side_effect=BrowserStartupError("起動失敗"),
            ),
            patch(
                "attendance_login.main.send_notification",
                side_effect=NotificationError("通知失敗"),
            ),
        ):
            self.assertEqual(run(config()), 7)

    def test_selector_error_returns_5(self) -> None:
        driver = MagicMock()
        with (
            patch(
                "attendance_login.main.create_driver", return_value=driver
            ),
            patch(
                "attendance_login.main.execute_login",
                side_effect=SelectorChangedError("要素なし"),
            ),
            patch("attendance_login.main.send_notification"),
        ):
            self.assertEqual(run(config()), 5)

    def test_network_error_returns_6(self) -> None:
        driver = MagicMock()
        with (
            patch(
                "attendance_login.main.create_driver", return_value=driver
            ),
            patch(
                "attendance_login.main.execute_login",
                side_effect=NetworkError("接続失敗"),
            ),
            patch("attendance_login.main.send_notification"),
        ):
            self.assertEqual(run(config()), 6)

    def test_success_quits_driver(self) -> None:
        driver = MagicMock()
        request_pacer = MagicMock()
        with (
            patch(
                "attendance_login.main.RequestPacer",
                return_value=request_pacer,
            ) as pacer_class,
            patch(
                "attendance_login.main.create_driver", return_value=driver
            ),
            patch("attendance_login.main.execute_login") as login,
            patch("attendance_login.main.enter_regular_work_hours") as enter,
            patch("attendance_login.main.record_daily_details") as details,
            patch("attendance_login.main.enter_workload") as workload,
        ):
            self.assertEqual(run(config()), 0)
        pacer_class.assert_called_once_with(5)
        login.assert_called_once_with(
            driver, config(), request_pacer=request_pacer
        )
        enter.assert_called_once_with(
            driver,
            timeout=10,
            start_time="09:00",
            end_time="17:45",
            dry_run=False,
            request_pacer=request_pacer,
        )
        details.assert_called_once_with(
            driver,
            timeout=10,
            work_place="出社",
            business_content_value="開発業務",
            dry_run=False,
            request_pacer=request_pacer,
        )
        workload.assert_not_called()
        driver.quit.assert_called_once()

    def test_login_only_does_not_change_attendance(self) -> None:
        driver = MagicMock()
        with (
            patch(
                "attendance_login.main.create_driver", return_value=driver
            ),
            patch("attendance_login.main.execute_login"),
            patch(
                "attendance_login.main.enter_regular_work_hours"
            ) as enter,
            patch("attendance_login.main.record_daily_details") as details,
            patch("attendance_login.main.enter_workload") as workload,
        ):
            self.assertEqual(run(config(), login_only=True), 0)
        enter.assert_not_called()
        details.assert_not_called()
        workload.assert_not_called()

    def test_dry_run_is_passed_to_attendance_operations(self) -> None:
        driver = MagicMock()
        with (
            patch(
                "attendance_login.main.create_driver", return_value=driver
            ),
            patch("attendance_login.main.execute_login"),
            patch(
                "attendance_login.main.enter_regular_work_hours"
            ) as enter,
            patch("attendance_login.main.record_daily_details") as details,
        ):
            self.assertEqual(run(config(), dry_run=True), 0)
        self.assertTrue(enter.call_args.kwargs["dry_run"])
        self.assertTrue(details.call_args.kwargs["dry_run"])

    def test_shared_pacer_is_passed_to_daily_request_and_workload(
        self,
    ) -> None:
        driver = MagicMock()
        request_pacer = MagicMock()
        enabled = replace(
            config(),
            daily_request_enabled=True,
            workload_enabled=True,
            workload_file=Path("/tmp/workload.json"),
        )
        with (
            patch(
                "attendance_login.main.RequestPacer",
                return_value=request_pacer,
            ),
            patch(
                "attendance_login.main.create_driver", return_value=driver
            ),
            patch("attendance_login.main.execute_login"),
            patch("attendance_login.main.enter_regular_work_hours"),
            patch("attendance_login.main.record_daily_details"),
            patch(
                "attendance_login.main.submit_daily_work_time_request"
            ) as daily_request,
            patch("attendance_login.main.load_workload", return_value=()),
            patch(
                "attendance_login.main.enter_workload",
                return_value=WorkloadResult.SAVED,
            ) as workload,
        ):
            self.assertEqual(run(enabled), 0)

        self.assertIs(
            daily_request.call_args.kwargs["request_pacer"], request_pacer
        )
        self.assertIs(
            workload.call_args.kwargs["request_pacer"], request_pacer
        )

    def test_non_workday_workload_blocks_application(self) -> None:
        driver = MagicMock()
        enabled = replace(
            config(),
            workload_enabled=True,
            workload_file=Path("/tmp/workload.json"),
            application_enabled=True,
        )
        with (
            patch(
                "attendance_login.main.create_driver", return_value=driver
            ),
            patch("attendance_login.main.execute_login"),
            patch("attendance_login.main.enter_regular_work_hours"),
            patch("attendance_login.main.record_daily_details"),
            patch("attendance_login.main.load_workload", return_value=()),
            patch(
                "attendance_login.main.enter_workload",
                return_value=WorkloadResult.NON_WORKDAY,
            ),
            patch(
                "attendance_login.main.confirm_monthly_application"
            ) as application,
        ):
            self.assertEqual(run(enabled), 0)
        application.assert_not_called()
