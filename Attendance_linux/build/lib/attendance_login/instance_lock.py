"""同一Chromeプロファイルでの多重起動を防止する。"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import os
from typing import Iterator, TextIO

from .errors import BrowserStartupError


def _try_lock(handle: TextIO) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        if not handle.read(1):
            handle.seek(0)
            handle.write("0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(handle: TextIO) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def profile_lock(user_data_dir: Path) -> Iterator[None]:
    lock_path = user_data_dir / ".attendance-login.lock"
    handle = lock_path.open("a+", encoding="utf-8")
    acquired = False
    try:
        try:
            _try_lock(handle)
            acquired = True
        except (OSError, BlockingIOError) as exc:
            raise BrowserStartupError(
                "同じChromeプロファイルを使用する処理が既に実行中です"
            ) from exc
        yield
    finally:
        try:
            if acquired:
                _unlock(handle)
        finally:
            handle.close()
