from datetime import date
from unittest import TestCase
from unittest.mock import MagicMock

from attendance_login import selectors
from attendance_login.daily_request import (
    DailyRequestResult,
    _request_from_application_row,
    _request_from_work_time_dialog,
    submit_daily_work_time_request,
)


class DailyRequestTest(TestCase):
    def test_dry_run_does_not_click_request_buttons(self) -> None:
        driver = MagicMock()
        heading = MagicMock()
        row = MagicMock()
        date_cell = MagicMock()
        date_cell.text = "31金"
        request_button = MagicMock()
        start_button = MagicMock()
        row.find_element.side_effect = lambda *locator: {
            selectors.DAILY_ROW_DATE: date_cell,
            selectors.DAILY_ROW_REQUEST_BUTTON: request_button,
            selectors.DAILY_ROW_START_BUTTON: start_button,
        }[locator]
        driver.find_elements.side_effect = [[heading], [row]]

        result = submit_daily_work_time_request(
            driver,
            target_date=date(2026, 7, 31),
            dry_run=True,
        )

        self.assertEqual(
            result,
            (
                DailyRequestResult.WOULD_SUBMIT,
                DailyRequestResult.WOULD_SUBMIT,
            ),
        )
        request_button.click.assert_not_called()
        start_button.click.assert_not_called()

    def test_work_time_dialog_clicks_request(self) -> None:
        driver = MagicMock()
        row = MagicMock()
        date_cell = MagicMock()
        date_cell.text = "31金"
        start_button = MagicMock()
        row.find_element.side_effect = lambda *locator: {
            selectors.DAILY_ROW_DATE: date_cell,
            selectors.DAILY_ROW_START_BUTTON: start_button,
        }[locator]
        driver.find_elements.side_effect = lambda *locator: (
            [row]
            if locator == selectors.TIME_ATTENDANCE_DAILY_ROWS
            else []
        )

        dialog = MagicMock()
        dialog_date = MagicMock()
        dialog_date.get_attribute.return_value = "2026-07-31T00:00:00Z"
        status = MagicMock()
        status.text = "未申請"
        request = MagicMock()
        dialog.find_element.side_effect = lambda *locator: {
            selectors.WORK_TIME_DIALOG_DATE: dialog_date,
            selectors.WORK_TIME_REQUEST_STATUS: status,
            selectors.WORK_TIME_REQUEST_BUTTON: request,
        }[locator]

        wait = MagicMock()
        wait.until.side_effect = [dialog, True]
        from unittest.mock import patch

        with patch(
            "attendance_login.daily_request.WebDriverWait", return_value=wait
        ):
            result = _request_from_work_time_dialog(
                driver, date(2026, 7, 31), 10, False
            )

        self.assertEqual(result, DailyRequestResult.SUBMITTED)
        start_button.click.assert_called_once()
        request.click.assert_called_once()

    def test_application_row_click_order(self) -> None:
        driver = MagicMock()
        heading = MagicMock()
        row = MagicMock()
        date_cell = MagicMock()
        date_cell.text = "31金"
        row_request = MagicMock()
        row.find_element.side_effect = lambda *locator: {
            selectors.DAILY_ROW_DATE: date_cell,
            selectors.DAILY_ROW_REQUEST_BUTTON: row_request,
        }[locator]
        driver.find_elements.side_effect = [[heading], [row]]

        dialog = MagicMock()
        dialog_date = MagicMock()
        dialog_date.get_attribute.return_value = "2026-07-31T00:00:00Z"
        change = MagicMock()
        submit = MagicMock()
        dialog.find_element.side_effect = lambda *locator: {
            selectors.DAILY_REQUEST_DIALOG_DATE: dialog_date,
            selectors.DAILY_REQUEST_WORK_TIME_CHANGE_BUTTON: change,
        }[locator]
        dialog.find_elements.side_effect = lambda *locator: (
            [submit]
            if locator == selectors.DAILY_REQUEST_SUBMIT_BUTTON
            else []
        )
        wait = MagicMock()
        wait.until.side_effect = [dialog, [submit], True]
        from unittest.mock import patch

        with patch(
            "attendance_login.daily_request.WebDriverWait", return_value=wait
        ):
            result = _request_from_application_row(
                driver, date(2026, 7, 31), 10, False
            )

        self.assertEqual(result, DailyRequestResult.SUBMITTED)
        row_request.click.assert_called_once()
        change.click.assert_called_once()
        submit.click.assert_called_once()
