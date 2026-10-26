from pathlib import Path

from PIL import Image

from photobook.scanner import scan_images


def test_scan_images_finds_supported_images(tmp_path: Path) -> None:
    photo_dir = tmp_path / "photo"
    photo_dir.mkdir()
    Image.new("RGB", (10, 10), "white").save(photo_dir / "b.jpg")
    Image.new("RGB", (10, 10), "black").save(photo_dir / "a.png")
    (photo_dir / "notes.txt").write_text("not an image", encoding="utf-8")

    result = scan_images(photo_dir, recursive=True, extensions=[".jpg", ".png"])
    assert [path.name for path in result] == ["a.png", "b.jpg"]


def test_scan_images_recursive(tmp_path: Path) -> None:
    photo_dir = tmp_path / "photo"
    nested = photo_dir / "trip"
    nested.mkdir(parents=True)
    Image.new("RGB", (10, 10), "white").save(nested / "image.jpg")

    assert len(scan_images(photo_dir, recursive=True, extensions=[".jpg"])) == 1
    assert scan_images(photo_dir, recursive=False, extensions=[".jpg"]) == []
