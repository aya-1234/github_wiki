from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG: dict[str, Any] = {
    "project": {"title": "Memories", "subtitle": "A Collection of Moments"},
    "input": {
        "directory": "photo",
        "recursive": True,
        "extensions": [".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"],
    },
    "output": {
        "directory": "artifact",
        "filename": "photobook.pdf",
        "page_size_mm": 210,
        "overwrite": False,
    },
    "design": {
        "margin_mm": 12,
        "cover_background": "#F5F2EA",
        "page_background": "#FFFFFF",
        "title_color": "#202020",
    },
    "layout": {
        "mode": "collage",
        "max_photos_per_page": 4,
        "gap_mm": 4,
        "random_seed": None,
    },
}


def load_config(path: Path) -> dict[str, Any]:
    """Load YAML settings and merge them with defaults."""
    if not path.is_file():
        raise FileNotFoundError(
            f"設定ファイルがありません: {path}. `photobook init` で作成してください。"
        )
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"YAMLの形式が不正です: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ValueError("設定ファイルの最上位はマッピングである必要があります。")

    result = _deep_merge(DEFAULT_CONFIG, loaded)
    _validate_config(result)
    return result


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _validate_config(config: dict) -> None:
    for section in ("project", "input", "output", "design", "layout"):
        if not isinstance(config.get(section), dict):
            raise ValueError(f"設定 `{section}` はマッピングである必要があります。")

    output = config["output"]
    if not isinstance(output.get("page_size_mm"), (int, float)):
        raise ValueError("output.page_size_mm は数値で指定してください。")
    if not 50 <= output["page_size_mm"] <= 500:
        raise ValueError("output.page_size_mm は50〜500 mmの範囲で指定してください。")
    if not isinstance(output.get("filename"), str) or not output["filename"].strip():
        raise ValueError("output.filename を指定してください。")
    if Path(output["filename"]).name != output["filename"] or output["filename"] in {".", ".."}:
        raise ValueError("output.filename にはファイル名のみ指定できます。")
    if not isinstance(config["input"].get("extensions"), list):
        raise ValueError("input.extensions はリストで指定してください。")
    if not isinstance(output.get("overwrite"), bool):
        raise ValueError("output.overwrite は true または false で指定してください。")
    if not isinstance(config["input"].get("recursive"), bool):
        raise ValueError("input.recursive は true または false で指定してください。")

    layout = config["layout"]

    if layout.get("mode") not in {"single", "collage"}:
        raise ValueError(
            "layout.mode は single または collage を指定してください。"
        )

    max_photos = layout.get("max_photos_per_page")
    if (
        not isinstance(max_photos, int)
        or isinstance(max_photos, bool)
        or not 1 <= max_photos <= 4
    ):
        raise ValueError(
            "layout.max_photos_per_page は1〜4の整数で指定してください。"
        )

    gap = layout.get("gap_mm")
    if (
        not isinstance(gap, (int, float))
        or isinstance(gap, bool)
        or not 0 <= gap <= 20
    ):
        raise ValueError("layout.gap_mm は0〜20 mmの数値で指定してください。")

    random_seed = layout.get("random_seed")
    if random_seed is not None and (
        not isinstance(random_seed, int)
        or isinstance(random_seed, bool)
    ):
        raise ValueError("layout.random_seed は整数または null で指定してください。")
