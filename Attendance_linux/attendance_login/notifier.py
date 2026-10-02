"""Webhook通知。"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
import json
import logging
import platform
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .errors import NotificationError

LOGGER = logging.getLogger(__name__)


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


@dataclass(frozen=True)
class Notification:
    title: str
    event: str
    message: str
    occurred_at: str
    host: str
    current_url: str


def send_notification(
    webhook_url: str,
    event: str,
    message: str,
    current_url: str,
    timeout: int,
) -> None:
    if not webhook_url:
        LOGGER.warning("WEBHOOK_URL未設定のため通知を省略します")
        return

    payload = Notification(
        title="勤怠ログインエラー",
        event=event,
        message=message,
        occurred_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        host=platform.node(),
        current_url=safe_url(current_url),
    )
    body = json.dumps(asdict(payload), ensure_ascii=False).encode("utf-8")
    request = Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            with urlopen(request, timeout=timeout) as response:
                if 200 <= response.status < 300:
                    return
                raise NotificationError(
                    f"WebhookがHTTP {response.status}を返しました"
                )
        except HTTPError as exc:
            if 400 <= exc.code < 500:
                raise NotificationError(
                    f"WebhookがHTTP {exc.code}を返しました"
                ) from exc
            last_error = exc
        except (URLError, TimeoutError) as exc:
            last_error = exc

        if attempt == 0:
            time.sleep(0.5)

    raise NotificationError("Webhook通知を送信できませんでした") from last_error
