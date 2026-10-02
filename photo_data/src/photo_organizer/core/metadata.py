import logging
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)
_EXIF_TAGS = {36867: "DateTimeOriginal", 36868: "DateTimeDigitized", 306: "DateTime"}


class MetadataReader:
    def __init__(self, fallback: str = "file_mtime") -> None:
        if fallback not in {"file_mtime", "skip"}:
            raise ValueError("fallback must be 'file_mtime' or 'skip'")
        self._fallback = fallback

    def get_capture_datetime(self, path: Path) -> datetime | None:
        try:
            with Image.open(path) as image:
                exif = image.getexif()
                for tag_id in _EXIF_TAGS:
                    value = exif.get(tag_id)
                    parsed = _parse_exif_datetime(value)
                    if parsed is not None:
                        return parsed
        except (OSError, UnidentifiedImageError, ValueError) as error:
            logger.debug("EXIF unavailable for %s: %s", path, error)
        if self._fallback == "skip":
            return None
        try:
            return datetime.fromtimestamp(path.stat().st_mtime)  # noqa: DTZ006 — use local filesystem time
        except OSError:
            logger.exception("Cannot read file timestamp for %s", path)
            return None


def _parse_exif_datetime(value: object) -> datetime | None:
    if not isinstance(value, (str, bytes)):
        return None
    if isinstance(value, bytes):
        value = value.decode("ascii", errors="ignore")
    try:
        return datetime.strptime(value.strip(), "%Y:%m:%d %H:%M:%S")  # noqa: DTZ007 — EXIF has no timezone
    except ValueError:
        return None
