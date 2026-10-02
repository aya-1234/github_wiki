"""ログイン画面の状態判定と操作。"""

from __future__ import annotations

from enum import Enum
import logging
import time
from urllib.parse import urlparse

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .config import Config
from .dom import scan_open_shadow_dom
from .errors import (
    AuthenticationTimeoutError,
    NetworkError,
    SelectorChangedError,
)
from .pacing import RequestPacer
from . import selectors

LOGGER = logging.getLogger(__name__)


class PageState(str, Enum):
    LOGGED_IN = "LOGGED_IN"
    ATTENDANCE_LOGIN = "ATTENDANCE_LOGIN"
    MS_ACCOUNT_SELECT = "MS_ACCOUNT_SELECT"
    MS_AUTH_IN_PROGRESS = "MS_AUTH_IN_PROGRESS"
    UNKNOWN = "UNKNOWN"


def _exists(driver: WebDriver, locator: tuple[str, str]) -> bool:
    try:
        return bool(driver.find_elements(*locator))
    except (StaleElementReferenceException, WebDriverException):
        return False


def _host_and_path(driver: WebDriver) -> tuple[str, str]:
    parsed = urlparse(driver.current_url)
    return parsed.hostname or "", parsed.path


def _find_attendance_frame(driver: WebDriver) -> WebElement | None:
    """全iframeを調べ、勤務表見出しを含むフレームを返す。"""
    driver.switch_to.default_content()
    try:
        frames, _ = scan_open_shadow_dom(driver)
        for frame in frames:
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                if _exists(driver, selectors.TIME_ATTENDANCE_HEADING):
                    return frame
            except (StaleElementReferenceException, WebDriverException):
                continue
        return None
    finally:
        driver.switch_to.default_content()


def _attendance_content_loaded(driver: WebDriver) -> bool:
    driver.switch_to.default_content()
    # トップレベルに勤務表が表示される構成にも対応する。
    if _exists(driver, selectors.TIME_ATTENDANCE_HEADING):
        return True
    host, path = _host_and_path(driver)
    if not (
        host == selectors.TIME_ATTENDANCE_HOST
        and selectors.TIME_ATTENDANCE_PATH in path
    ):
        return False
    return _find_attendance_frame(driver) is not None


def _element_count(driver: WebDriver, locator: tuple[str, str]) -> str:
    """診断用に要素数を返す。WebDriverエラー自体も判別可能にする。"""
    try:
        return str(len(driver.find_elements(*locator)))
    except (StaleElementReferenceException, WebDriverException) as exc:
        return f"確認失敗({type(exc).__name__})"


def _log_detection_diagnostics(driver: WebDriver) -> None:
    """状態判定に使う要素の検出結果を、タイムアウト時に一度だけ記録する。"""
    try:
        driver.switch_to.default_content()
        host, path = _host_and_path(driver)
        results = [
            f"location={host}{path}",
            f"expected_attendance_host={host == selectors.TIME_ATTENDANCE_HOST}",
            f"expected_attendance_path={selectors.TIME_ATTENDANCE_PATH in path}",
            "salesforce_header="
            f"{_element_count(driver, selectors.SALESFORCE_HEADER)}",
            f"attendance_tab={_element_count(driver, selectors.TIME_ATTENDANCE_TAB)}",
            "attendance_iframe="
            f"{_element_count(driver, selectors.TIME_ATTENDANCE_IFRAME)}",
            "salesforce_login_form="
            f"{_element_count(driver, selectors.SALESFORCE_LOGIN_FORM)}",
            f"sso_login_button={_element_count(driver, selectors.SSO_LOGIN_BUTTON)}",
            f"ms_account_list={_element_count(driver, selectors.MS_ACCOUNT_LIST)}",
        ]

        frames, shadow_root_count = scan_open_shadow_dom(driver)
        results.append(f"all_iframes={len(frames)}")
        results.append(
            "open_shadow_roots="
            f"{shadow_root_count if shadow_root_count is not None else '確認失敗'}"
        )
        attendance_frame = _find_attendance_frame(driver)
        results.append(
            "attendance_frame_with_heading="
            f"{'検出' if attendance_frame is not None else '未検出'}"
        )
        LOGGER.warning("画面要素診断: %s", ", ".join(results))
    except WebDriverException as exc:
        LOGGER.warning(
            "画面要素診断を取得できませんでした: %s", type(exc).__name__
        )


def detect_state(driver: WebDriver) -> PageState:
    driver.switch_to.default_content()
    if _attendance_content_loaded(driver):
        return PageState.LOGGED_IN

    host, _ = _host_and_path(driver)
    if (
        host == selectors.SALESFORCE_LOGIN_HOST
        and _exists(driver, selectors.SALESFORCE_LOGIN_FORM)
        and _exists(driver, selectors.SSO_LOGIN_BUTTON)
    ):
        return PageState.ATTENDANCE_LOGIN

    if host == selectors.MICROSOFT_LOGIN_HOST:
        if _exists(driver, selectors.MS_ACCOUNT_LIST):
            return PageState.MS_ACCOUNT_SELECT
        return PageState.MS_AUTH_IN_PROGRESS

    return PageState.UNKNOWN


def _click_sso(
    driver: WebDriver, request_pacer: RequestPacer | None = None
) -> None:
    button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(selectors.SSO_LOGIN_BUTTON)
    )
    if request_pacer is not None:
        request_pacer.wait_for_slot()
    button.click()
    LOGGER.info("Salesforce SSOログインを開始しました")


def _select_account(
    driver: WebDriver,
    target_account: str,
    request_pacer: RequestPacer | None = None,
) -> None:
    # Microsoftの保存済みアカウントタイルでは、idがアカウント文字列と一致する。
    try:
        tile = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, target_account))
        )
    except TimeoutException as exc:
        raise SelectorChangedError(
            "対象Microsoftアカウントが選択画面に見つかりません"
        ) from exc
    if request_pacer is not None:
        request_pacer.wait_for_slot()
    tile.click()
    LOGGER.info("設定済みMicrosoftアカウントを選択しました")


def execute_login(
    driver: WebDriver,
    config: Config,
    *,
    request_pacer: RequestPacer | None = None,
) -> None:
    if request_pacer is not None:
        request_pacer.wait_for_slot()
    try:
        driver.get(config.top_url)
    except TimeoutException as exc:
        raise NetworkError("勤怠管理システムのページ読込がタイムアウトしました") from exc
    except WebDriverException as exc:
        raise NetworkError("勤怠管理システムへ接続できません") from exc

    deadline = time.monotonic() + config.login_timeout
    sso_clicked = False
    account_selected = False
    last_state = PageState.UNKNOWN

    while time.monotonic() < deadline:
        try:
            state = detect_state(driver)
        except WebDriverException:
            state = PageState.UNKNOWN

        if state != last_state:
            LOGGER.info("画面状態: %s", state.value)
            last_state = state

        if state is PageState.LOGGED_IN:
            LOGGER.info("勤務表画面の表示を確認しました")
            return

        if state is PageState.ATTENDANCE_LOGIN and not sso_clicked:
            _click_sso(driver, request_pacer)
            sso_clicked = True
        elif state is PageState.MS_ACCOUNT_SELECT and not account_selected:
            _select_account(driver, config.target_account, request_pacer)
            account_selected = True

        time.sleep(0.5)

    driver.switch_to.default_content()
    host, path = _host_and_path(driver)
    safe_location = f"{host}{path}"
    if last_state is PageState.UNKNOWN:
        _log_detection_diagnostics(driver)
        raise SelectorChangedError(
            f"既知の画面要素を検出できませんでした: {safe_location}"
        )
    raise AuthenticationTimeoutError(
        f"ログイン完了を確認できませんでした: state={last_state.value}, "
        f"location={safe_location}"
    )
