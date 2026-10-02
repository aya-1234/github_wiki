from pathlib import Path

import pytest

from photo_organizer.core.file_operator import FileOperator


def test_copy_preserves_source_and_verifies_content(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "out" / "photo.jpg"
    source.write_bytes(b"photo bytes")

    FileOperator().copy(source, destination)

    assert source.read_bytes() == destination.read_bytes() == b"photo bytes"


def test_move_transfers_file(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "out" / "photo.jpg"
    source.write_bytes(b"photo bytes")

    FileOperator().move(source, destination)

    assert not source.exists()
    assert destination.read_bytes() == b"photo bytes"


def test_existing_destination_is_preserved_on_copy_failure(tmp_path: Path) -> None:
    source, destination = tmp_path / "source", tmp_path / "destination"
    source.write_bytes(b"new")
    destination.write_bytes(b"existing")

    with pytest.raises(FileExistsError):
        FileOperator().copy(source, destination)

    assert source.read_bytes() == b"new"
    assert destination.read_bytes() == b"existing"
