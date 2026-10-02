"""サーバー通信を伴う自動操作の実行間隔を制御する。"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import time


LOGGER = logging.getLogger(__name__)


@dataclass
class RequestPacer:
    """サーバー操作の開始時刻を一定間隔以上に保つ。"""

    delay_seconds: float
    _last_request_started_at: float | None = field(
        default=None, init=False, repr=False
    )

    def wait_for_slot(self) -> None:
        """必要な残り時間だけ待機し、今回の操作開始時刻を記録する。"""
        now = time.monotonic()
        if self._last_request_started_at is not None:
            elapsed = now - self._last_request_started_at
            remaining = self.delay_seconds - elapsed
            if remaining > 0:
                LOGGER.debug(
                    "サーバー負荷軽減のため操作を %.2f 秒待機します",
                    remaining,
                )
                time.sleep(remaining)
                now = time.monotonic()
        self._last_request_started_at = now
