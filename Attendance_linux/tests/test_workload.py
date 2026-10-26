import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, patch

from attendance_login import selectors
from attendance_login.errors import ConfigurationError
from attendance_login.workload import (
    WorkloadEntry,
    load_workload,
    normalized_workload_time,
    totals_match,
    workload_minutes,
    enter_workload,
    WorkloadResult,
)


class WorkloadDataTest(TestCase):
    def test_converts_time_to_minutes(self) -> None:
        self.assertEqual(workload_minutes("7:45"), 465)
        self.assertEqual(normalized_workload_time("7:45"), "07:45")

    def test_rejects_invalid_time(self) -> None:
        with self.assertRaises(ConfigurationError):
            workload_minutes("7.75")

    def test_totals_match_actual_work_time(self) -> None:
        entries = (
            WorkloadEntry("JOB_A", "04:00"),
            WorkloadEntry("JOB_B", "03:45"),
        )
        self.assertTrue(totals_match(entries, "07:45"))
        self.assertFalse(totals_match(entries, "08:00"))

    def test_tolerance_is_applied(self) -> None:
        entries = (WorkloadEntry("JOB_A", "07:44"),)
        self.assertTrue(totals_match(entries, "07:45", 1))

    def test_loads_entries_for_target_date(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "workload.json"
            path.write_text(
                json.dumps(
                    {
                        "2026-07-31": [
                            {"job_code": "JOB_A", "time": "7:45"}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            entries = load_workload(path, date(2026, 7, 31))
        self.assertEqual(entries, (WorkloadEntry("JOB_A", "07:45"),))

    def test_missing_date_returns_empty_entries(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "workload.json"
            path.write_text("{}", encoding="utf-8")
            entries = load_workload(path, date(2026, 7, 31))
        self.assertEqual(entries, ())

    def test_duplicate_job_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "workload.json"
            path.write_text(
                json.dumps(
                    {
                        "2026-07-31": [
                            {"job_code": "JOB_A", "time": "01:00"},
                            {"job_code": "JOB_A", "time": "02:00"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigurationError):
                load_workload(path, date(2026, 7, 31))


class WorkloadOperationTest(TestCase):
    def _screen(self, current: str = ""):
        driver = MagicMock()
        heading = MagicMock()
        row = MagicMock()
        date_cell = MagicMock()
        date_cell.text = "31金"
        open_button = MagicMock()
        row.get_attribute.return_value = (
            "timesheet-pc-main-content-timesheet-daily-row "
            "timesheet-pc-main-content-timesheet-daily-row--day-type-workday"
        )
        row.find_element.side_effect = lambda *locator: {
            selectors.DAILY_ROW_DATE: date_cell,
            selectors.DAILY_ROW_WORKLOAD_BUTTON: open_button,
        }[locator]
        driver.find_elements.side_effect = [[heading], [row]]

        dialog = MagicMock()
        title = MagicMock()
        date_input = MagicMock()
        date_input.get_attribute.return_value = "2026/07/31(金)"
        actual = MagicMock()
        actual.text = "07:45"
        task = MagicMock()
        code = MagicMock()
        code.text = "JOB_A"
        time_input = MagicMock()
        time_input.get_attribute.return_value = current
        task.find_elements.return_value = [code]
        task.find_element.return_value = time_input
        dialog.find_element.side_effect = lambda *locator: {
            selectors.WORKLOAD_DIALOG_TITLE: title,
            selectors.WORKLOAD_DIALOG_DATE: date_input,
        }[locator]
        dialog.find_elements.side_effect = lambda *locator: {
            selectors.WORKLOAD_ACTUAL_TIME: [actual],
            selectors.WORKLOAD_TASK_ROWS: [task],
        }[locator]
        return driver, dialog, open_button, time_input

    def test_dry_run_does_not_change_input(self) -> None:
        driver, dialog, open_button, time_input = self._screen("")
        wait = MagicMock()
        wait.until.return_value = dialog
        with patch(
            "attendance_login.workload.WebDriverWait", return_value=wait
        ):
            result = enter_workload(
                driver,
                (WorkloadEntry("JOB_A", "07:45"),),
                target_date=date(2026, 7, 31),
                dry_run=True,
            )
        self.assertEqual(result, WorkloadResult.WOULD_SAVE)
        open_button.click.assert_called_once()
        time_input.send_keys.assert_not_called()

    def test_existing_different_value_is_protected(self) -> None:
        driver, dialog, _, time_input = self._screen("01:00")
        wait = MagicMock()
        wait.until.return_value = dialog
        with patch(
            "attendance_login.workload.WebDriverWait", return_value=wait
        ):
            result = enter_workload(
                driver,
                (WorkloadEntry("JOB_A", "07:45"),),
                target_date=date(2026, 7, 31),
            )
        self.assertEqual(result, WorkloadResult.CONFLICT)
        time_input.send_keys.assert_not_called()

    def test_same_value_is_not_saved_again(self) -> None:
        driver, dialog, _, time_input = self._screen("07:45")
        wait = MagicMock()
        wait.until.return_value = dialog
        with patch(
            "attendance_login.workload.WebDriverWait", return_value=wait
        ):
            result = enter_workload(
                driver,
                (WorkloadEntry("JOB_A", "07:45"),),
                target_date=date(2026, 7, 31),
            )
        self.assertEqual(result, WorkloadResult.ALREADY_SET)
        time_input.send_keys.assert_not_called()

    def test_non_workday_is_skipped(self) -> None:
        driver = MagicMock()
        heading = MagicMock()
        row = MagicMock()
        date_cell = MagicMock()
        date_cell.text = "31金"
        open_button = MagicMock()
        row.get_attribute.return_value = (
            "timesheet-pc-main-content-timesheet-daily-row "
            "timesheet-pc-main-content-timesheet-daily-row--day-type-holiday"
        )
        row.find_element.side_effect = lambda *locator: {
            selectors.DAILY_ROW_DATE: date_cell,
            selectors.DAILY_ROW_WORKLOAD_BUTTON: open_button,
        }[locator]
        driver.find_elements.side_effect = [[heading], [row]]

        result = enter_workload(
            driver,
            (WorkloadEntry("JOB_A", "07:45"),),
            target_date=date(2026, 7, 31),
        )

        self.assertEqual(result, WorkloadResult.NON_WORKDAY)
        open_button.click.assert_not_called()
