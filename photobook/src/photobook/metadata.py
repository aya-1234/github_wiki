from datetime import datetime
from pathlib import Path

from PIL import Image


_EXIF_DATE_TAGS = (36867, 36868, 306)  # DateTimeOriginal, DateTimeDigitized, DateTime


def image_datetime(path: Path) -> datetime:
    """Use EXIF capture time where available; otherwise use file mtime."""
    try:
        with Image.open(path) as image:
            exif = image.getexif()
            for tag in _EXIF_DATE_TAGS:
                value = exif.get(tag)
                if not value:
                    continue
                try:
                    return datetime.strptime(str(value).strip(), "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    continue
    except (OSError, ValueError):
        # Scanner normally filters unreadable files; mtime is a safe fallback.
        pass

    return datetime.fromtimestamp(path.stat().st_mtime)


def sort_by_capture_time(paths: list[Path]) -> list[Path]:
    """Sort by capture time; use normalized path as a deterministic tie-breaker."""
    return sorted(paths, key=lambda p: (image_datetime(p), p.as_posix().casefold()))
