from pathlib import Path

from photo_organizer.core.scanner import PhotoScanner


def test_scan_recurses_and_filters_extensions(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / "one.JPG").write_bytes(b"a")
    (nested / "two.jpeg").write_bytes(b"b")
    (nested / "notes.txt").write_text("ignore")

    assert PhotoScanner((".jpg", ".jpeg")).scan(tmp_path) == [nested / "two.jpeg", tmp_path / "one.JPG"]


def test_scan_missing_directory_raises(tmp_path: Path) -> None:
    try:
        PhotoScanner((".jpg",)).scan(tmp_path / "missing")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Missing source should raise FileNotFoundError")
