from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image

from photo_organizer.config.settings import Settings
from photo_organizer.core.file_operator import FileOperator
from photo_organizer.core.organizer import Organizer


def _photo(path: Path, contents: bytes = b"same") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)


def test_organizer_copies_by_mtime_and_skips_duplicate(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    _photo(source / "a.jpg")
    _photo(source / "b.jpg")
    settings = Settings(supported_extensions=(".jpg",))

    result = Organizer(settings).run(source, destination, "copy")

    assert result.processed == 2
    assert result.copied == 1
    assert result.skipped == 1
    assert (destination / "2026").exists() or any(destination.iterdir())
    assert (source / "a.jpg").exists() and (source / "b.jpg").exists()


def test_organizer_move_cancel_keeps_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    Image.new("RGB", (2, 2), "red").save(source / "photo.jpg")
    Image.new("RGB", (2, 2), "blue").save(source / "photo2.jpg")
    checks = 0

    def cancel_after_first() -> bool:
        nonlocal checks
        checks += 1
        return checks > 1

    result = Organizer(Settings()).run(source, destination, "move", cancelled=cancel_after_first)

    assert result.cancelled
    assert result.moved == 1
    assert result.processed == 1
    assert (source / "photo2.jpg").exists()


def test_move_mode_does_not_remove_duplicate_source(tmp_path: Path) -> None:
    source, destination = tmp_path / "source", tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    photo = source / "photo.jpg"
    Image.new("RGB", (2, 2), "red").save(photo)
    captured = datetime.fromtimestamp(photo.stat().st_mtime)  # noqa: DTZ006 — use local filesystem time
    dated = destination / f"{captured.year:04d}" / f"{captured.month:02d}" / f"{captured.day:02d}"
    dated.mkdir(parents=True)
    (dated / "existing.jpg").write_bytes(photo.read_bytes())

    result = Organizer(Settings()).run(source, destination, "move")

    assert result.skipped == 1
    assert photo.exists()


def test_organizer_avoids_overwriting_different_same_name(tmp_path: Path) -> None:
    source, destination = tmp_path / "source", tmp_path / "destination"
    source.mkdir()
    photo = source / "photo.jpg"
    Image.new("RGB", (2, 2), "red").save(photo)
    captured = datetime.fromtimestamp(photo.stat().st_mtime)  # noqa: DTZ006 — use local filesystem time
    dated = destination / f"{captured.year:04d}" / f"{captured.month:02d}" / f"{captured.day:02d}"
    dated.mkdir(parents=True)
    (dated / "photo.jpg").write_bytes(b"different content")

    result = Organizer(Settings()).run(source, destination, "copy")

    assert result.copied == 1
    assert (dated / "photo_001.jpg").read_bytes() == photo.read_bytes()


def test_organizer_rejects_overlapping_source_and_destination(tmp_path: Path) -> None:
    source = tmp_path / "photos"
    source.mkdir()
    try:
        Organizer(Settings()).run(source, tmp_path, "copy")
    except ValueError as error:
        assert "overlap" in str(error)
    else:
        raise AssertionError("Overlapping paths must be rejected")


def test_organizer_records_file_error_and_continues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, destination = tmp_path / "source", tmp_path / "destination"
    source.mkdir()
    _photo(source / "a.jpg", b"first")
    _photo(source / "b.jpg", b"second")
    original_copy = FileOperator.copy

    def fail_first(self: FileOperator, source_path: Path, destination_path: Path) -> None:
        if source_path.name == "a.jpg":
            raise OSError("simulated copy failure")
        original_copy(self, source_path, destination_path)

    monkeypatch.setattr(FileOperator, "copy", fail_first)
    result = Organizer(Settings(supported_extensions=(".jpg",))).run(source, destination, "copy")

    assert result.errors == 1
    assert result.copied == 1
