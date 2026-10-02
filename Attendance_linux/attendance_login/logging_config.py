"""秘密情報を出力しないログ設定。"""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def configure_logging(
    level: str,
    log_file: Path | None = None,
    retention_days: int = 30,
) -> None:
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            backupCount=retention_days,
            encoding="utf-8",
        )
        handlers.append(file_handler)
    for handler in handlers:
        handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level))
    for handler in handlers:
        root.addHandler(handler)
