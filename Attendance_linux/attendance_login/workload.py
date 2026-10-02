"""保存済みジョブへ日別工数を安全に入力する。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import json
import logging
from pathlib import Path
import re

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support.ui import WebDriverWait

from . import selectors
from .errors import ConfigurationError, SelectorChangedError
from .pacing import RequestPacer
from .work_hours import (
    WORKDAY_CLASS,
    _find_today_row,
    _set_input_value,
    _switch_to_attendance_content,
    _today_in_japan,
)

LOGGER = logging.getLogger(__name__)
TIME_PATTERN = re.compile(r"(\d{1,3}):([0-5]\d)")


@dataclass(frozen=True)
class WorkloadEntry:
    job_code: str
    time: str

    @property
    def minutes(self) -> int:
        return workload_minutes(self.time)


class WorkloadResult(str, Enum):
    SAVED = "SAVED"
    WOULD_SAVE = "WOULD_SAVE"
    ALREADY_SET = "ALREADY_SET"
    NON_WORKDAY = "NON_WORKDAY"
    CONFLICT = "CONFLICT"
    NO_DATA = "NO_DATA"


def workload_minutes(value: str) -> int:
    match = TIME_PATTERN.fullmatch(value.strip())
    if not match:
        raise ConfigurationError("工数は HHH:MM 形式で指定してください")
    hours, minutes = (int(part) for part in match.groups())
    return hours * 60 + minutes


def normalized_workload_time(value: str) -> str:
    minutes = workload_minutes(value)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def load_workload(path: Path, target_date: date) -> tuple[WorkloadEntry, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError(
            "WORKLOAD_FILE をJSONとして読み込めません"
        ) from exc
    if not isinstance(payload, dict):
        raise ConfigurationError("工数JSONのルートはオブジェクトにしてください")
    raw_entries = payload.get(target_date.isoformat(), [])
    if not isinstance(raw_entries, list):
        raise ConfigurationError("対象日の工数は配列で指定してください")

    entries: list[WorkloadEntry] = []
    seen: set[str] = set()
    for raw in raw_entries:
        if not isinstance(raw, dict):
            raise ConfigurationError("工数明細はオブジェクトで指定してください")
        job_code = str(raw.get("job_code", "")).strip()
        time = str(raw.get("time", "")).strip()
        if not job_code or any(c in job_code for c in "\r\n"):
            raise ConfigurationError("工数の job_code が不正です")
        if job_code in seen:
            raise ConfigurationError("同じ job_code を重複指定できません")
        seen.add(job_code)
        entries.append(
            WorkloadEntry(job_code, normalized_workload_time(time))
        )
    return tuple(entries)


def totals_match(
    entries: tuple[WorkloadEntry, ...],
    actual_time: str,
    tolerance_minutes: int = 0,
) -> bool:
    return (
        abs(sum(entry.minutes for entry in entries) - workload_minutes(actual_time))
        <= tolerance_minutes
    )


def _task_row_code(row: WebElement) -> str:
    values = [
        element.text.strip()
        for element in row.find_elements(*selectors.WORKLOAD_TASK_JOB_CODE)
        if element.text.strip()
    ]
    return values[0] if values else ""


def enter_workload(
    driver: WebDriver,
    entries: tuple[WorkloadEntry, ...],
    *,
    target_date: date | None = None,
    timeout: int = 10,
    tolerance_minutes: int = 0,
    allow_overwrite: bool = False,
    dry_run: bool = False,
    request_pacer: RequestPacer | None = None,
) -> WorkloadResult:
    """既に画面にあるジョブだけを更新し、未知のジョブでは停止する。"""
    target_date = target_date or _today_in_japan()
    if not entries:
        LOGGER.info("当日の工数データはありません")
        return WorkloadResult.NO_DATA
    _switch_to_attendance_content(driver)
    try:
        row = _find_today_row(driver, target_date)
        if WORKDAY_CLASS not in (row.get_attribute("class") or "").split():
            LOGGER.info("当日は勤務日ではないため工数を入力しません")
            return WorkloadResult.NON_WORKDAY
        if request_pacer is not None:
            request_pacer.wait_for_slot()
        row.find_element(*selectors.DAILY_ROW_WORKLOAD_BUTTON).click()
        dialog = WebDriverWait(driver, timeout).until(
            lambda current: (
                current.find_element(*selectors.WORKLOAD_DIALOG)
                if current.find_elements(*selectors.WORKLOAD_DIALOG)
                else False
            )
        )
        dialog.find_element(*selectors.WORKLOAD_DIALOG_TITLE)
        date_value = (
            dialog.find_element(*selectors.WORKLOAD_DIALOG_DATE)
            .get_attribute("value")
            or ""
        )
        expected_date = f"{target_date.year:04d}/{target_date.month:02d}/{target_date.day:02d}"
        if not date_value.startswith(expected_date):
            raise SelectorChangedError("工数入力画面の対象日が一致しません")

        actual_times = dialog.find_elements(*selectors.WORKLOAD_ACTUAL_TIME)
        actual_time = next(
            (
                element.text.strip()
                for element in actual_times
                if TIME_PATTERN.fullmatch(element.text.strip())
            ),
            "",
        )
        if not actual_time or not totals_match(
            entries, actual_time, tolerance_minutes
        ):
            raise SelectorChangedError("工数合計と実労働時間が一致しません")

        task_rows = dialog.find_elements(*selectors.WORKLOAD_TASK_ROWS)
        rows_by_code = {_task_row_code(task): task for task in task_rows}
        missing = [entry.job_code for entry in entries if entry.job_code not in rows_by_code]
        if missing:
            raise SelectorChangedError(
                "保存済み画面にないジョブは自動追加できません"
            )

        changes: list[tuple[WebElement, str]] = []
        for entry in entries:
            time_input = rows_by_code[entry.job_code].find_element(
                *selectors.WORKLOAD_TASK_TIME_INPUT
            )
            current = normalized_workload_time(
                time_input.get_attribute("value") or "0:00"
            )
            if current == entry.time:
                continue
            if current != "00:00" and not allow_overwrite:
                LOGGER.warning("既存工数を保護するため上書きしません")
                return WorkloadResult.CONFLICT
            changes.append((time_input, entry.time))

        if not changes:
            LOGGER.info("当日の工数は設定済みです")
            return WorkloadResult.ALREADY_SET
        if dry_run:
            LOGGER.info("確認モード: 当日の工数は入力対象です")
            return WorkloadResult.WOULD_SAVE
        for element, value in changes:
            _set_input_value(element, value)
        if request_pacer is not None:
            request_pacer.wait_for_slot()
        dialog.find_element(*selectors.WORKLOAD_SAVE_AND_CLOSE_BUTTON).click()
        WebDriverWait(driver, timeout).until(
            lambda current: not current.find_elements(
                *selectors.WORKLOAD_DIALOG
            )
        )
        LOGGER.info("当日の工数を保存しました")
        return WorkloadResult.SAVED
    except TimeoutException as exc:
        raise SelectorChangedError(
            "工数入力または保存確認がタイムアウトしました"
        ) from exc
    except NoSuchElementException as exc:
        raise SelectorChangedError(
            "工数入力に必要な画面要素を検出できませんでした"
        ) from exc
    except WebDriverException as exc:
        raise SelectorChangedError("工数入力操作に失敗しました") from exc
    finally:
        try:
            driver.switch_to.default_content()
        except WebDriverException:
            pass
