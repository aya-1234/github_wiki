"""月次申請の事前確認と二重申請防止。"""

from __future__ import annotations

from enum import Enum
import logging

from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

from . import selectors
from .errors import ApplicationBlockedError, SelectorChangedError
from .work_hours import _switch_to_attendance_content

LOGGER = logging.getLogger(__name__)


class ApplicationResult(str, Enum):
    WOULD_SUBMIT = "WOULD_SUBMIT"
    ALREADY_SUBMITTED = "ALREADY_SUBMITTED"
    BLOCKED = "BLOCKED"


SUBMITTED_STATUSES = frozenset({"申請中", "承認済", "確定済"})
BLOCKED_STATUSES = frozenset({"差戻し", "却下", "取消"})


def decide_application(status: str) -> ApplicationResult:
    normalized = status.strip()
    if normalized in SUBMITTED_STATUSES:
        return ApplicationResult.ALREADY_SUBMITTED
    if normalized in BLOCKED_STATUSES:
        return ApplicationResult.BLOCKED
    if normalized == "未申請":
        return ApplicationResult.WOULD_SUBMIT
    raise SelectorChangedError("判定できない月次申請ステータスです")


def confirm_monthly_application(
    driver: WebDriver,
    *,
    confirm_only: bool = True,
    auto_submit: bool = False,
) -> ApplicationResult:
    """状態を確認する。確定画面の保存HTML取得までは送信しない。"""
    _switch_to_attendance_content(driver)
    try:
        status = driver.find_element(*selectors.MONTHLY_STATUS).text.strip()
        result = decide_application(status)
        if result is ApplicationResult.ALREADY_SUBMITTED:
            LOGGER.info("月次勤務は申請済みのため再申請しません")
            return result
        if result is ApplicationResult.BLOCKED:
            raise ApplicationBlockedError(
                "月次勤務は差戻し等のため自動申請できません"
            )

        button = driver.find_element(*selectors.MONTHLY_CONFIRM_BUTTON)
        if not button.is_enabled():
            raise SelectorChangedError("月次勤務確定ボタンが無効です")
        if confirm_only or not auto_submit:
            LOGGER.info("確認モード: 月次勤務は申請対象です")
            return ApplicationResult.WOULD_SUBMIT

        # 申請は不可逆性が高い。未申請時の確認ダイアログを保存HTMLで
        # 照合できるまでは、設定が誤って有効でもクリックしない。
        raise SelectorChangedError(
            "月次勤務確定の確認画面が未照合のため自動申請を停止しました"
        )
    except NoSuchElementException as exc:
        raise SelectorChangedError(
            "月次申請に必要な画面要素を検出できませんでした"
        ) from exc
    except WebDriverException as exc:
        raise SelectorChangedError("月次申請の確認操作に失敗しました") from exc
    finally:
        try:
            driver.switch_to.default_content()
        except WebDriverException:
            pass
