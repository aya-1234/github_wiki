from datetime import datetime
from pathlib import Path

from PIL import Image

from photo_organizer.core.metadata import MetadataReader


def test_exif_datetime_is_preferred(tmp_path: Path) -> None:
    path = tmp_path / "photo.jpg"
    image = Image.new("RGB", (2, 2))
    exif = Image.Exif()
    exif[36867] = "2020:02:03 04:05:06"
    image.save(path, exif=exif)

    assert MetadataReader().get_capture_datetime(path) == datetime(2020, 2, 3, 4, 5, 6)  # noqa: DTZ001 — EXIF is timezone-naive


def test_file_mtime_fallback_and_skip(tmp_path: Path) -> None:
    path = tmp_path / "not-an-image.jpg"
    path.write_bytes(b"bad")

    assert MetadataReader("file_mtime").get_capture_datetime(path) is not None
    assert MetadataReader("skip").get_capture_datetime(path) is None
