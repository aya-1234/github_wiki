from datetime import date
from unittest import TestCase
from unittest.mock import MagicMock, patch

from attendance_login import selectors
from attendance_login.work_hours import (
    DailyDetailsResult,
    WorkHoursResult,
    _normalized_time,
    _requires_manual_adjustment,
    _switch_to_attendance_content,
    enter_regular_work_hours,
    record_daily_details,
)


TARGET_DATE = date(2026, 7, 31)


def driver_with_row(
    *,
    row_class: str,
    start: str = "",
    end: str = "",
) -> tuple[MagicMock, MagicMock]:
    driver = MagicMock()
    frame = MagicMock()
    row = MagicMock()
    date_cell = MagicMock()
    date_cell.text = "31金"
    start_button = MagicMock()
    start_button.text = start
    end_button = MagicMock()
    end_button.text = end
    heading = MagicMock()

    row.get_attribute.return_value = row_class

    def row_find_element(*locator):
        if locator == selectors.DAILY_ROW_DATE:
            return date_cell
        if locator == selectors.DAILY_ROW_START_BUTTON:
            return start_button
        if locator == selectors.DAILY_ROW_END_BUTTON:
            return end_button
        raise AssertionError(f"unexpected locator: {locator}")

    row.find_element.side_effect = row_find_element
    driver.find_elements.side_effect = [[], [frame], [heading], [row]]
    return driver, start_button


class WorkHoursDecisionTest(TestCase):
    def test_direct_attendance_page_does_not_switch_to_frame(self) -> None:
        driver = MagicMock()
        heading = MagicMock()
        driver.find_elements.return_value = [heading]

        _switch_to_attendance_content(driver)

        driver.switch_to.frame.assert_not_called()

    def test_normalizes_single_digit_hour(self) -> None:
        self.assertEqual(_normalized_time("9:00"), "09:00")

    def test_regular_or_empty_values_do_not_require_manual_adjustment(
        self,
    ) -> None:
        self.assertFalse(_requires_manual_adjustment("", ""))
        self.assertFalse(_requires_manual_adjustment("09:00", "17:45"))

    def test_overtime_value_requires_manual_adjustment(self) -> None:
        self.assertTrue(_requires_manual_adjustment("09:00", "19:15"))

    def test_non_workday_is_skipped(self) -> None:
        driver, start_button = driver_with_row(
            row_class=(
                "timesheet-pc-main-content-timesheet-daily-row "
                "timesheet-pc-main-content-timesheet-daily-row--day-type-holiday"
            )
        )
        result = enter_regular_work_hours(
            driver, target_date=TARGET_DATE
        )
        self.assertEqual(result, WorkHoursResult.NON_WORKDAY)
        start_button.click.assert_not_called()

    def test_existing_overtime_is_not_overwritten(self) -> None:
        driver, start_button = driver_with_row(
            row_class=(
                "timesheet-pc-main-content-timesheet-daily-row "
                "timesheet-pc-main-content-timesheet-daily-row--day-type-workday"
            ),
            start="09:00",
            end="19:15",
        )
        result = enter_regular_work_hours(
            driver, target_date=TARGET_DATE
        )
        self.assertEqual(result, WorkHoursResult.MANUAL_ADJUSTMENT)
        start_button.click.assert_not_called()

    def test_regular_hours_are_not_saved_again(self) -> None:
        driver, start_button = driver_with_row(
            row_class=(
                "timesheet-pc-main-content-timesheet-daily-row "
                "timesheet-pc-main-content-timesheet-daily-row--day-type-workday"
            ),
            start="09:00",
            end="17:45",
        )
        result = enter_regular_work_hours(
            driver, target_date=TARGET_DATE
        )
        self.assertEqual(result, WorkHoursResult.ALREADY_SET)
        start_button.click.assert_not_called()

    def test_dry_run_does_not_open_work_time_dialog(self) -> None:
        driver, start_button = driver_with_row(
            row_class=(
                "timesheet-pc-main-content-timesheet-daily-row "
                "timesheet-pc-main-content-timesheet-daily-row--day-type-workday"
            )
        )
        result = enter_regular_work_hours(
            driver,
            target_date=TARGET_DATE,
            dry_run=True,
        )
        self.assertEqual(result, WorkHoursResult.WOULD_SAVE)
        start_button.click.assert_not_called()

    def test_empty_workday_is_filled_and_saved(self) -> None:
        driver, start_button = driver_with_row(
            row_class=(
                "timesheet-pc-main-content-timesheet-daily-row "
                "timesheet-pc-main-content-timesheet-daily-row--day-type-workday"
            )
        )
        dialog = MagicMock()
        title = MagicMock()
        title.text = "勤務時間入力"
        dialog_date = MagicMock()
        dialog_date.get_attribute.return_value = (
            "2026-07-31T00:00:00.000Z"
        )
        start_input = MagicMock()
        start_input.get_attribute.return_value = ""
        end_input = MagicMock()
        end_input.get_attribute.return_value = ""
        save_button = MagicMock()
        heading = MagicMock()

        def dialog_find_element(*locator):
            mapping = {
                selectors.WORK_TIME_DIALOG_TITLE: title,
                selectors.WORK_TIME_DIALOG_DATE: dialog_date,
                selectors.WORK_TIME_START_INPUT: start_input,
                selectors.WORK_TIME_END_INPUT: end_input,
                selectors.WORK_TIME_SAVE_BUTTON: save_button,
            }
            return mapping[locator]

        dialog.find_element.side_effect = dialog_find_element
        wait = MagicMock()
        wait.until.side_effect = [dialog, True, True]
        with patch(
            "attendance_login.work_hours.WebDriverWait",
            return_value=wait,
        ):
            result = enter_regular_work_hours(
                driver, target_date=TARGET_DATE
            )

        self.assertEqual(result, WorkHoursResult.SAVED)
        start_button.click.assert_called_once()
        start_input.send_keys.assert_called()
        end_input.send_keys.assert_called()
        save_button.click.assert_called_once()


class DailyDetailsTest(TestCase):
    def test_business_content_is_saved_for_office_workday(self) -> None:
        driver = MagicMock()
        frame = MagicMock()
        heading = MagicMock()
        row = MagicMock()
        date_cell = MagicMock()
        date_cell.text = "31金"
        workplace = MagicMock()
        workplace.get_attribute.side_effect = (
            lambda name: "出社" if name in {"value", "title"} else None
        )
        business_content = MagicMock()
        business_content.get_attribute.return_value = ""
        save_button = MagicMock()
        save_button.is_enabled.return_value = True
        row.get_attribute.return_value = (
            "timesheet-pc-main-content-timesheet-daily-row "
            "timesheet-pc-main-content-timesheet-daily-row--day-type-workday"
        )

        def row_find_element(*locator):
            mapping = {
                selectors.DAILY_ROW_DATE: date_cell,
                selectors.DAILY_ROW_WORKPLACE_BUTTON: workplace,
                selectors.DAILY_ROW_BUSINESS_CONTENT_INPUT: business_content,
                selectors.DAILY_ROW_SAVE_BUTTON: save_button,
            }
            return mapping[locator]

        row.find_element.side_effect = row_find_element
        driver.find_elements.side_effect = [[], [frame], [heading], [row]]
        wait = MagicMock()
        wait.until.side_effect = [True, True, True]
        with patch(
            "attendance_login.work_hours.WebDriverWait",
            return_value=wait,
        ):
            result = record_daily_details(
                driver, target_date=TARGET_DATE
            )

        self.assertEqual(result, DailyDetailsResult.SAVED)
        workplace.click.assert_not_called()
        business_content.send_keys.assert_called()
        save_button.click.assert_called_once()
