from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from selenium.common.exceptions import TimeoutException

from attendance_login.config import Config
from attendance_login.errors import NetworkError, SelectorChangedError
from attendance_login.login import (
    PageState,
    _find_attendance_frame,
    _log_detection_diagnostics,
    _select_account,
    execute_login,
)


def config() -> Config:
    return Config(
        top_url="https://example.com/",
        user_data_dir=Path("/tmp"),
        profile_directory=None,
        target_account="user@example.com",
        webhook_url="",
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


class LoginErrorTest(TestCase):
    def test_logged_in_does_not_navigate_to_iframe_source(self) -> None:
        driver = MagicMock()
        with (
            patch(
                "attendance_login.login.detect_state",
                return_value=PageState.LOGGED_IN,
            ),
            patch(
                "attendance_login.login.time.monotonic",
                side_effect=[0.0, 0.0],
            ),
        ):
            execute_login(driver, config())

        driver.get.assert_called_once_with(config().top_url)

    def test_finds_attendance_content_in_second_iframe(self) -> None:
        driver = MagicMock()
        unrelated_frame = MagicMock()
        attendance_frame = MagicMock()
        heading = MagicMock()
        driver.find_elements.side_effect = [
            [unrelated_frame, attendance_frame],
            [],
            [heading],
        ]

        found = _find_attendance_frame(driver)

        self.assertIs(found, attendance_frame)
        self.assertEqual(driver.switch_to.frame.call_count, 2)

    def test_detection_diagnostics_reports_missing_attendance_elements(self) -> None:
        driver = MagicMock()
        driver.current_url = (
            "https://meitecgroup.lightning.force.com/"
            "lightning/n/tex__TimeAttendance?token=secret"
        )
        driver.find_elements.return_value = []

        with self.assertLogs("attendance_login.login", level="WARNING") as logs:
            _log_detection_diagnostics(driver)

        message = logs.output[0]
        self.assertIn("expected_attendance_host=True", message)
        self.assertIn("expected_attendance_path=True", message)
        self.assertIn("salesforce_header=0", message)
        self.assertIn("attendance_tab=0", message)
        self.assertIn("attendance_iframe=0", message)
        self.assertIn("all_iframes=0", message)
        self.assertIn("attendance_frame_with_heading=未検出", message)
        self.assertNotIn("token", message)
        self.assertNotIn("secret", message)

    def test_missing_account_becomes_selector_error(self) -> None:
        wait = MagicMock()
        wait.until.side_effect = TimeoutException()
        with patch("attendance_login.login.WebDriverWait", return_value=wait):
            with self.assertRaises(SelectorChangedError) as raised:
                _select_account(MagicMock(), "user@example.com")
        self.assertNotIn("user@example.com", str(raised.exception))

    def test_page_load_timeout_becomes_network_error(self) -> None:
        driver = MagicMock()
        driver.get.side_effect = TimeoutException()
        with self.assertRaises(NetworkError):
            execute_login(driver, config())

    def test_unknown_salesforce_elements_become_selector_error(self) -> None:
        driver = MagicMock()
        driver.current_url = "https://meitecgroup.my.salesforce.com/"
        with (
            patch(
                "attendance_login.login.detect_state",
                return_value=PageState.UNKNOWN,
            ),
            patch(
                "attendance_login.login._log_detection_diagnostics"
            ) as diagnostics,
            patch(
                "attendance_login.login.time.monotonic",
                side_effect=[0.0, 2.0],
            ),
        ):
            with self.assertRaises(SelectorChangedError):
                execute_login(driver, config())
        diagnostics.assert_called_once_with(driver)
