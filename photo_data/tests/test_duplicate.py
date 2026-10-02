from pathlib import Path

from photo_organizer.core.duplicate import DuplicateDetector, generate_unique_path


def test_duplicate_by_content_and_size(tmp_path: Path) -> None:
    first, same, different = (tmp_path / name for name in ("first", "same", "different"))
    first.write_bytes(b"photo")
    same.write_bytes(b"photo")
    different.write_bytes(b"other")
    detector = DuplicateDetector()

    assert detector.is_duplicate(first, same)
    assert not detector.is_duplicate(first, different)
    assert detector.find_duplicate(first, tmp_path) == same


def test_unique_filename_uses_incrementing_suffix(tmp_path: Path) -> None:
    original = tmp_path / "IMG.JPG"
    original.touch()
    (tmp_path / "IMG_001.JPG").touch()

    assert generate_unique_path(original).name == "IMG_002.JPG"
