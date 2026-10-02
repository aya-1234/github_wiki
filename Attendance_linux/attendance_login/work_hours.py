"""勤務表の当日行へ定時の出退勤時刻を入力する。"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from enum import Enum
import logging
import re

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from . import selectors
from .dom import scan_open_shadow_dom
from .errors import SelectorChangedError
from .pacing import RequestPacer

LOGGER = logging.getLogger(__name__)

REGULAR_START_TIME = "09:00"
REGULAR_END_TIME = "17:45"
REGULAR_WORKPLACE = "出社"
REGULAR_BUSINESS_CONTENT = "開発業務"
WORKDAY_CLASS = "timesheet-pc-main-content-timesheet-daily-row--day-type-workday"
JAPAN_STANDARD_TIME = timezone(timedelta(hours=9), name="Asia/Tokyo")


class WorkHoursResult(str, Enum):
    SAVED = "SAVED"
    WOULD_SAVE = "WOULD_SAVE"
    ALREADY_SET = "ALREADY_SET"
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT"
    NON_WORKDAY = "NON_WORKDAY"


class DailyDetailsResult(str, Enum):
    SAVED = "SAVED"
    WOULD_SAVE = "WOULD_SAVE"
    ALREADY_SET = "ALREADY_SET"
    NON_WORKDAY = "NON_WORKDAY"


def _normalized_time(value: str) -> str:
    value = value.strip()
    if not value or value in {"-", "—", "--:--"}:
        return ""
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", value)
    if not match:
        return value
    hour, minute = (int(part) for part in match.groups())
    if hour > 23 or minute > 59:
        return value
    return f"{hour:02d}:{minute:02d}"


def _requires_manual_adjustment(
    start: str,
    end: str,
    expected_start: str = REGULAR_START_TIME,
    expected_end: str = REGULAR_END_TIME,
) -> bool:
    normalized_start = _normalized_time(start)
    normalized_end = _normalized_time(end)
    return (
        bool(normalized_start) and normalized_start != expected_start
    ) or (
        bool(normalized_end) and normalized_end != expected_end
    )


def _today_in_japan() -> date:
    return datetime.now(JAPAN_STANDARD_TIME).date()


def _button_text(row: WebElement, locator: tuple[str, str]) -> str:
    return row.find_element(*locator).text.strip()


def _find_today_row(driver: WebDriver, target_date: date) -> WebElement:
    rows = driver.find_elements(*selectors.TIME_ATTENDANCE_DAILY_ROWS)
    matches: list[WebElement] = []
    for row in rows:
        try:
            date_text = row.find_element(*selectors.DAILY_ROW_DATE).text.strip()
        except (NoSuchElementException, StaleElementReferenceException):
            continue
        match = re.match(r"(\d{1,2})", date_text)
        if match and int(match.group(1)) == target_date.day:
            matches.append(row)

    if len(matches) != 1:
        raise SelectorChangedError(
            "勤務表から当日の日付行を一意に特定できませんでした"
        )
    return matches[0]


def _set_input_value(element: WebElement, value: str) -> None:
    element.click()
    element.send_keys(Keys.CONTROL, "a")
    element.send_keys(value)


def _dialog_matches_date(dialog: WebElement, target_date: date) -> bool:
    raw = dialog.find_element(*selectors.WORK_TIME_DIALOG_DATE).get_attribute(
        "datetime"
    )
    return bool(raw and raw.startswith(target_date.isoformat()))


def _find_workplace_option(
    driver: WebDriver, expected_label: str
) -> WebElement | bool:
    for option in driver.find_elements(*selectors.WORKPLACE_OPTIONS):
        if option.text.strip() == expected_label:
            return option
    return False


def _switch_to_attendance_content(driver: WebDriver) -> None:
    """トップレベルまたは全iframeから勤務表の表示領域へ切り替える。"""
    driver.switch_to.default_content()
    if driver.find_elements(*selectors.TIME_ATTENDANCE_HEADING):
        return
    frames, _ = scan_open_shadow_dom(driver)
    for frame in frames:
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)
            if driver.find_elements(*selectors.TIME_ATTENDANCE_HEADING):
                return
        except (StaleElementReferenceException, WebDriverException):
            continue
    driver.switch_to.default_content()
    raise SelectorChangedError("勤務表の表示領域を特定できませんでした")


def enter_regular_work_hours(
    driver: WebDriver,
    *,
    target_date: date | None = None,
    timeout: int = 10,
    start_time: str = REGULAR_START_TIME,
    end_time: str = REGULAR_END_TIME,
    dry_run: bool = False,
    request_pacer: RequestPacer | None = None,
) -> WorkHoursResult:
    """当日が勤務日なら定時を保存し、定時外の既存値は保護する。"""
    target_date = target_date or _today_in_japan()
    _switch_to_attendance_content(driver)

    try:
        row = _find_today_row(driver, target_date)
        if WORKDAY_CLASS not in (row.get_attribute("class") or "").split():
            LOGGER.info("当日は勤務日ではないため勤務時間を入力しません")
            return WorkHoursResult.NON_WORKDAY

        start_button = row.find_element(*selectors.DAILY_ROW_START_BUTTON)
        end_button = row.find_element(*selectors.DAILY_ROW_END_BUTTON)
        current_start = start_button.text.strip()
        current_end = end_button.text.strip()

        if _requires_manual_adjustment(
            current_start, current_end, start_time, end_time
        ):
            LOGGER.info(
                "当日は定時外の勤務時間が設定されているため上書きしません"
            )
            return WorkHoursResult.MANUAL_ADJUSTMENT
        if (
            _normalized_time(current_start) == start_time
            and _normalized_time(current_end) == end_time
        ):
            LOGGER.info("当日の勤務時間は設定済みです")
            return WorkHoursResult.ALREADY_SET
        if dry_run:
            LOGGER.info("確認モード: 当日の勤務時間は入力対象です")
            return WorkHoursResult.WOULD_SAVE

        if request_pacer is not None:
            request_pacer.wait_for_slot()
        start_button.click()
        dialog = WebDriverWait(driver, timeout).until(
            lambda current_driver: (
                current_driver.find_element(*selectors.WORK_TIME_DIALOG)
                if current_driver.find_elements(*selectors.WORK_TIME_DIALOG)
                else False
            )
        )
        title = dialog.find_element(*selectors.WORK_TIME_DIALOG_TITLE).text.strip()
        if title != "勤務時間入力" or not _dialog_matches_date(
            dialog, target_date
        ):
            raise SelectorChangedError(
                "勤務時間入力画面の対象日を確認できませんでした"
            )

        start_input = dialog.find_element(*selectors.WORK_TIME_START_INPUT)
        end_input = dialog.find_element(*selectors.WORK_TIME_END_INPUT)
        dialog_start = start_input.get_attribute("value") or ""
        dialog_end = end_input.get_attribute("value") or ""
        if _requires_manual_adjustment(
            dialog_start, dialog_end, start_time, end_time
        ):
            LOGGER.info(
                "入力画面に定時外の勤務時間があるため上書きしません"
            )
            return WorkHoursResult.MANUAL_ADJUSTMENT

        if _normalized_time(dialog_start) != start_time:
            _set_input_value(start_input, start_time)
        if _normalized_time(dialog_end) != end_time:
            _set_input_value(end_input, end_time)

        if request_pacer is not None:
            request_pacer.wait_for_slot()
        dialog.find_element(*selectors.WORK_TIME_SAVE_BUTTON).click()
        WebDriverWait(driver, timeout).until(
            lambda current_driver: not current_driver.find_elements(
                *selectors.WORK_TIME_DIALOG
            )
        )

        def saved_values_visible(_driver: WebDriver) -> bool:
            refreshed_row = _find_today_row(driver, target_date)
            return (
                _normalized_time(
                    _button_text(
                        refreshed_row, selectors.DAILY_ROW_START_BUTTON
                    )
                )
                == start_time
                and _normalized_time(
                    _button_text(
                        refreshed_row, selectors.DAILY_ROW_END_BUTTON
                    )
                )
                == end_time
            )

        WebDriverWait(driver, timeout).until(saved_values_visible)
        LOGGER.info("当日の勤務時間を定時で保存しました")
        return WorkHoursResult.SAVED
    except TimeoutException as exc:
        raise SelectorChangedError(
            "勤務時間の入力または保存確認がタイムアウトしました"
        ) from exc
    except NoSuchElementException as exc:
        raise SelectorChangedError(
            "勤務時間入力に必要な画面要素を検出できませんでした"
        ) from exc
    except WebDriverException as exc:
        raise SelectorChangedError("勤務時間の入力操作に失敗しました") from exc
    finally:
        try:
            driver.switch_to.default_content()
        except WebDriverException:
            pass


def record_daily_details(
    driver: WebDriver,
    *,
    target_date: date | None = None,
    timeout: int = 10,
    work_place: str = REGULAR_WORKPLACE,
    business_content_value: str = REGULAR_BUSINESS_CONTENT,
    dry_run: bool = False,
    request_pacer: RequestPacer | None = None,
) -> DailyDetailsResult:
    """当日行へ勤務場所と業務内容を設定し、保存反映まで待つ。"""
    target_date = target_date or _today_in_japan()
    _switch_to_attendance_content(driver)

    try:
        row = _find_today_row(driver, target_date)
        if WORKDAY_CLASS not in (row.get_attribute("class") or "").split():
            LOGGER.info("当日は勤務日ではないため勤務情報を入力しません")
            return DailyDetailsResult.NON_WORKDAY

        workplace = row.find_element(*selectors.DAILY_ROW_WORKPLACE_BUTTON)
        business_content = row.find_element(
            *selectors.DAILY_ROW_BUSINESS_CONTENT_INPUT
        )
        current_workplace = (
            workplace.get_attribute("value")
            or workplace.get_attribute("title")
            or workplace.text
            or ""
        ).strip()
        current_business_content = (
            business_content.get_attribute("value") or ""
        ).strip()

        workplace_changed = current_workplace != work_place
        content_changed = current_business_content != business_content_value
        if dry_run and (workplace_changed or content_changed):
            LOGGER.info("確認モード: 当日の勤務場所と業務内容は入力対象です")
            return DailyDetailsResult.WOULD_SAVE

        changed = False
        if workplace_changed:
            workplace.click()
            office_option = WebDriverWait(driver, timeout).until(
                lambda current_driver: _find_workplace_option(
                    current_driver, work_place
                )
            )
            office_option.click()
            changed = True

        if content_changed:
            _set_input_value(business_content, business_content_value)
            changed = True

        if not changed:
            LOGGER.info("当日の勤務場所と業務内容は設定済みです")
            return DailyDetailsResult.ALREADY_SET

        save_button = row.find_element(*selectors.DAILY_ROW_SAVE_BUTTON)
        WebDriverWait(driver, timeout).until(
            lambda _driver: save_button.is_enabled()
        )
        if request_pacer is not None:
            request_pacer.wait_for_slot()
        save_button.click()
        WebDriverWait(driver, timeout).until(EC.staleness_of(row))

        # リロードで行が再生成された後、再取得した値を正として完了判定する。
        def saved_details_visible(_driver: WebDriver) -> bool:
            refreshed_row = _find_today_row(driver, target_date)
            refreshed_workplace = refreshed_row.find_element(
                *selectors.DAILY_ROW_WORKPLACE_BUTTON
            )
            refreshed_content = refreshed_row.find_element(
                *selectors.DAILY_ROW_BUSINESS_CONTENT_INPUT
            )
            workplace_value = (
                refreshed_workplace.get_attribute("value")
                or refreshed_workplace.get_attribute("title")
                or refreshed_workplace.text
                or ""
            ).strip()
            content_value = (
                refreshed_content.get_attribute("value") or ""
            ).strip()
            return (
                workplace_value == work_place
                and content_value == business_content_value
            )

        WebDriverWait(driver, timeout).until(saved_details_visible)
        LOGGER.info("当日の勤務場所と業務内容を保存しました")
        return DailyDetailsResult.SAVED
    except TimeoutException as exc:
        raise SelectorChangedError(
            "勤務場所と業務内容の保存確認がタイムアウトしました"
        ) from exc
    except NoSuchElementException as exc:
        raise SelectorChangedError(
            "勤務情報の入力に必要な画面要素を検出できませんでした"
        ) from exc
    except WebDriverException as exc:
        raise SelectorChangedError("勤務情報の入力操作に失敗しました") from exc
    finally:
        try:
            driver.switch_to.default_content()
        except WebDriverException:
            pass
