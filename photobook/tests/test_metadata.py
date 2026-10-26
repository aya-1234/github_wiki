import os
from datetime import datetime
from pathlib import Path

from PIL import Image

from photobook.metadata import image_datetime, sort_by_capture_time


def test_falls_back_to_file_mtime(tmp_path: Path) -> None:
    path = tmp_path / "plain.jpg"
    Image.new("RGB", (10, 10), "white").save(path)
    expected = 1_700_000_000
    os.utime(path, (expected, expected))
    assert image_datetime(path) == datetime.fromtimestamp(expected)


def test_sort_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "a.jpg"
    second = tmp_path / "b.jpg"
    Image.new("RGB", (10, 10), "white").save(first)
    Image.new("RGB", (10, 10), "white").save(second)
    os.utime(first, (1_700_000_000, 1_700_000_000))
    os.utime(second, (1_600_000_000, 1_600_000_000))
    assert sort_by_capture_time([first, second]) == [second, first]
