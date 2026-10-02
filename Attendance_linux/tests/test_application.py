from unittest import TestCase
from unittest.mock import MagicMock

from attendance_login import selectors
from attendance_login.application import (
    ApplicationResult,
    confirm_monthly_application,
    decide_application,
)
from attendance_login.errors import SelectorChangedError


class ApplicationDecisionTest(TestCase):
    def test_unsubmitted_month_is_candidate(self) -> None:
        self.assertEqual(
            decide_application("未申請"), ApplicationResult.WOULD_SUBMIT
        )

    def test_submitted_month_is_not_submitted_twice(self) -> None:
        for status in ("申請中", "承認済", "確定済"):
            with self.subTest(status=status):
                self.assertEqual(
                    decide_application(status),
                    ApplicationResult.ALREADY_SUBMITTED,
                )

    def test_returned_month_is_blocked(self) -> None:
        self.assertEqual(
            decide_application("差戻し"), ApplicationResult.BLOCKED
        )

    def test_unknown_status_stops_processing(self) -> None:
        with self.assertRaises(SelectorChangedError):
            decide_application("不明")

    def test_confirmation_mode_does_not_click_submit(self) -> None:
        driver = MagicMock()
        heading = MagicMock()
        status = MagicMock()
        status.text = "未申請"
        button = MagicMock()
        button.is_enabled.return_value = True
        driver.find_elements.return_value = [heading]
        driver.find_element.side_effect = lambda *locator: {
            selectors.MONTHLY_STATUS: status,
            selectors.MONTHLY_CONFIRM_BUTTON: button,
        }[locator]

        result = confirm_monthly_application(driver, confirm_only=True)

        self.assertEqual(result, ApplicationResult.WOULD_SUBMIT)
        button.click.assert_not_called()

    def test_auto_submit_stops_before_unverified_dialog(self) -> None:
        driver = MagicMock()
        heading = MagicMock()
        status = MagicMock()
        status.text = "未申請"
        button = MagicMock()
        button.is_enabled.return_value = True
        driver.find_elements.return_value = [heading]
        driver.find_element.side_effect = lambda *locator: {
            selectors.MONTHLY_STATUS: status,
            selectors.MONTHLY_CONFIRM_BUTTON: button,
        }[locator]

        with self.assertRaises(SelectorChangedError):
            confirm_monthly_application(
                driver, confirm_only=False, auto_submit=True
            )
        button.click.assert_not_called()
