from pathlib import Path

from PIL import Image, UnidentifiedImageError


def scan_images(directory: Path, recursive: bool, extensions: list[str]) -> list[Path]:
    """Return supported, readable image files in deterministic order."""
    if not directory.is_dir():
        raise FileNotFoundError(f"画像ディレクトリがありません: {directory}")

    allowed = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions}
    candidates = directory.rglob("*") if recursive else directory.iterdir()
    images: list[Path] = []
    invalid: list[Path] = []

    for path in candidates:
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        try:
            with Image.open(path) as image:
                image.verify()
            images.append(path)
        except (UnidentifiedImageError, OSError, ValueError):
            invalid.append(path)

    for path in invalid:
        print(f"警告: 読み込めない画像をスキップします: {path}")

    return sorted(images, key=lambda p: p.as_posix().casefold())
