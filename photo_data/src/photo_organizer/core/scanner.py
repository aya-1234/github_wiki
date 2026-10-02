import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PhotoScanner:
    def __init__(self, supported_extensions: tuple[str, ...]) -> None:
        self._extensions = {extension.lower() for extension in supported_extensions}

    def scan(self, source: Path) -> list[Path]:
        if not source.exists() or not source.is_dir():
            raise FileNotFoundError(f"Input directory does not exist: {source}")
        try:
            return sorted(
                (path for path in source.rglob("*") if path.is_file() and path.suffix.lower() in self._extensions),
                key=lambda path: str(path).casefold(),
            )
        except OSError:
            logger.exception("Failed while scanning %s", source)
            raise
