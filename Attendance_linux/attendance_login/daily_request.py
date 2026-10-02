"""勤務時間入力画面と申請列から日次の勤務時間変更を申請する。"""

from __future__ import annotations

from datetime import date
from enum import Enum
import logging

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from . import selectors
from .errors import SelectorChangedError
from .pacing import RequestPacer
from .work_hours import (
    _dialog_matches_date,
    _find_today_row,
    _switch_to_attendance_content,
    _today_in_japan,
)

LOGGER = logging.getLogger(__name__)


class DailyRequestResult(str, Enum):
    SUBMITTED = "SUBMITTED"
    ALREADY_SUBMITTED = "ALREADY_SUBMITTED"
    WOULD_SUBMIT = "WOULD_SUBMIT"


SUBMITTED_STATUSES = frozenset({"申請中", "承認済", "申請済み"})


def _request_from_work_time_dialog(
    driver: WebDriver,
    target_date: date,
    timeout: int,
    dry_run: bool,
    request_pacer: RequestPacer | None = None,
) -> DailyRequestResult:
    row = _find_today_row(driver, target_date)
    if request_pacer is not None:
        request_pacer.wait_for_slot()
    row.find_element(*selectors.DAILY_ROW_START_BUTTON).click()
    dialog = WebDriverWait(driver, timeout).until(
        lambda current: (
            current.find_element(*selectors.WORK_TIME_DIALOG)
            if current.find_elements(*selectors.WORK_TIME_DIALOG)
            else False
        )
    )
    if not _dialog_matches_date(dialog, target_date):
        raise SelectorChangedError(
            "勤務時間入力画面の申請対象日が一致しません"
        )
    status = dialog.find_element(
        *selectors.WORK_TIME_REQUEST_STATUS
    ).text.strip()
    if status in SUBMITTED_STATUSES:
        LOGGER.info("勤務時間入力画面では申請済みです")
        dialog.find_element(*selectors.WORK_TIME_CANCEL_BUTTON).click()
        return DailyRequestResult.ALREADY_SUBMITTED
    if status != "未申請":
        raise SelectorChangedError("勤務時間入力画面の申請状態を判定できません")
    if dry_run:
        LOGGER.info("確認モード: 勤務時間入力画面の申請は対象です")
        return DailyRequestResult.WOULD_SUBMIT
    if request_pacer is not None:
        request_pacer.wait_for_slot()
    dialog.find_element(*selectors.WORK_TIME_REQUEST_BUTTON).click()
    WebDriverWait(driver, timeout).until(
        lambda current: (
            not current.find_elements(*selectors.WORK_TIME_DIALOG)
            or (
                current.find_elements(*selectors.WORK_TIME_REQUEST_STATUS)
                and current.find_element(
                    *selectors.WORK_TIME_REQUEST_STATUS
                ).text.strip()
                != "未申請"
            )
        )
    )
    if driver.find_elements(*selectors.WORK_TIME_DIALOG):
        driver.find_element(*selectors.WORK_TIME_DIALOG).find_element(
            *selectors.WORK_TIME_CANCEL_BUTTON
        ).click()
    LOGGER.info("勤務時間入力画面の申請ボタンをクリックしました")
    return DailyRequestResult.SUBMITTED


def _request_from_application_row(
    driver: WebDriver,
    target_date: date,
    timeout: int,
    dry_run: bool,
    request_pacer: RequestPacer | None = None,
) -> DailyRequestResult:
    _switch_to_attendance_content(driver)
    row = _find_today_row(driver, target_date)
    if request_pacer is not None:
        request_pacer.wait_for_slot()
    row.find_element(*selectors.DAILY_ROW_REQUEST_BUTTON).click()
    dialog = WebDriverWait(driver, timeout).until(
        lambda current: (
            current.find_element(*selectors.DAILY_REQUEST_DIALOG)
            if current.find_elements(*selectors.DAILY_REQUEST_DIALOG)
            else False
        )
    )
    raw_date = dialog.find_element(
        *selectors.DAILY_REQUEST_DIALOG_DATE
    ).get_attribute("datetime")
    if not raw_date or not raw_date.startswith(target_date.isoformat()):
        raise SelectorChangedError("申請画面の対象日が一致しません")

    change_button = dialog.find_element(
        *selectors.DAILY_REQUEST_WORK_TIME_CHANGE_BUTTON
    )
    if request_pacer is not None:
        request_pacer.wait_for_slot()
    change_button.click()
    # 申請済み画面では申請ボタンがなく「取消し」だけが表示される。
    if dialog.find_elements(*selectors.DAILY_REQUEST_WITHDRAW_BUTTON):
        LOGGER.info("申請行の勤務時間変更は申請済みです")
        return DailyRequestResult.ALREADY_SUBMITTED
    submit_buttons = WebDriverWait(driver, timeout).until(
        lambda _current: (
            dialog.find_elements(*selectors.DAILY_REQUEST_SUBMIT_BUTTON)
            or False
        )
    )
    if dry_run:
        LOGGER.info("確認モード: 申請行の勤務時間変更は申請対象です")
        return DailyRequestResult.WOULD_SUBMIT
    if request_pacer is not None:
        request_pacer.wait_for_slot()
    submit_buttons[0].click()
    WebDriverWait(driver, timeout).until(
        lambda current: not current.find_elements(
            *selectors.DAILY_REQUEST_DIALOG
        )
    )
    LOGGER.info("申請行から勤務時間変更を申請しました")
    return DailyRequestResult.SUBMITTED


def submit_daily_work_time_request(
    driver: WebDriver,
    *,
    target_date: date | None = None,
    timeout: int = 10,
    dry_run: bool = False,
    request_pacer: RequestPacer | None = None,
) -> tuple[DailyRequestResult, DailyRequestResult]:
    """指定された2経路を順番に実行する。"""
    target_date = target_date or _today_in_japan()
    _switch_to_attendance_content(driver)
    try:
        if dry_run:
            _find_today_row(driver, target_date)
            LOGGER.info(
                "確認モード: 勤務時間入力画面と申請行は申請対象です"
            )
            return (
                DailyRequestResult.WOULD_SUBMIT,
                DailyRequestResult.WOULD_SUBMIT,
            )
        dialog_result = _request_from_work_time_dialog(
            driver, target_date, timeout, False, request_pacer
        )
        # 1経路目のクリックでDOMが再生成される可能性があるため再探索する。
        row_result = _request_from_application_row(
            driver, target_date, timeout, False, request_pacer
        )
        return dialog_result, row_result
    except TimeoutException as exc:
        raise SelectorChangedError(
            "勤務時間変更の申請操作がタイムアウトしました"
        ) from exc
    except NoSuchElementException as exc:
        raise SelectorChangedError(
            "勤務時間変更の申請に必要な画面要素を検出できませんでした"
        ) from exc
    except WebDriverException as exc:
        raise SelectorChangedError("勤務時間変更の申請操作に失敗しました") from exc
    finally:
        try:
            driver.switch_to.default_content()
        except WebDriverException:
            pass
