import random
from dataclasses import dataclass
from pathlib import Path
import math
import random

@dataclass(frozen=True)
class PhotoPage:
    """A PDF page containing one or more photographs."""

    image_paths: tuple[Path, ...]


def build_pages(
    images: list[Path],
    mode: str = "single",
    max_photos_per_page: int = 4,
) -> list[PhotoPage]:
    """Build photo pages while preserving the input order."""
    if mode not in {"single", "collage"}:
        raise ValueError("layout.mode は single または collage を指定してください。")

    if not isinstance(max_photos_per_page, int) or isinstance(max_photos_per_page, bool):
        raise ValueError("layout.max_photos_per_page は整数で指定してください。")

    if not 1 <= max_photos_per_page <= 4:
        raise ValueError("layout.max_photos_per_page は1〜4の範囲で指定してください。")

    if mode == "single":
        return [PhotoPage(image_paths=(image,)) for image in images]

    return [
        PhotoPage(image_paths=tuple(images[index:index + max_photos_per_page]))
        for index in range(0, len(images), max_photos_per_page)
    ]

def build_random_placements(
    count: int,
    page_size: float,
    margin: float,
    seed: int | None = None,
) -> list[tuple[float, float, float, float, float]]:
    """非対称グリッドを基準に写真の配置をランダム生成する。

    Returns:
        (center_x, center_y, box_width, box_height, angle_degrees)
    """
    if not 1 <= count <= 4:
        raise ValueError("写真枚数は1〜4枚である必要があります。")
    if page_size <= 0 or margin < 0 or margin * 2 >= page_size:
        raise ValueError("ページサイズまたは余白の設定が不正です。")

    rng = random.Random(seed)
    content = page_size - 2 * margin

    # center_x, center_y, width, height をページ内の比率で定義する。
    # 大小の異なる写真を組み合わせた非対称レイアウト。
    layouts = {
        1: [
            (0.50, 0.50, 0.78, 0.78),
        ],
        2: [
            (0.32, 0.50, 0.56, 0.76),
            (0.74, 0.50, 0.36, 0.52),
        ],
        3: [
            (0.31, 0.50, 0.54, 0.76),
            (0.73, 0.29, 0.38, 0.36),
            (0.72, 0.72, 0.36, 0.38),
        ],
        4: [
            (0.30, 0.50, 0.52, 0.74),
            (0.73, 0.20, 0.37, 0.24),
            (0.72, 0.50, 0.36, 0.25),
            (0.74, 0.80, 0.37, 0.24),
        ],
    }

    placements = []

    for base_x, base_y, base_w, base_h in layouts[count]:
        # 写真ごとにサイズを変える。
        scale = rng.uniform(0.88, 1.08)
        width = content * base_w * scale
        height = content * base_h * scale
        angle = rng.uniform(-10.0, 10.0)

        # 配置位置も少しだけ揺らす。
        center_x = margin + content * (
            base_x + rng.uniform(-0.025, 0.025)
        )
        center_y = margin + content * (
            base_y + rng.uniform(-0.025, 0.025)
        )

        # 回転後の外接矩形を使ってページ内に収める。
        radians = math.radians(angle)
        half_width = (
            abs(width * math.cos(radians))
            + abs(height * math.sin(radians))
        ) / 2
        half_height = (
            abs(width * math.sin(radians))
            + abs(height * math.cos(radians))
        ) / 2

        # ページに収まるように、必要な場合だけ縮小する。
        max_extent = content / 2
        if half_width > max_extent or half_height > max_extent:
            scale_down = min(
                max_extent / half_width,
                max_extent / half_height,
            )
            width *= scale_down
            height *= scale_down
            half_width *= scale_down
            half_height *= scale_down

        center_x = min(
            max(center_x, margin + half_width),
            page_size - margin - half_width,
        )
        center_y = min(
            max(center_y, margin + half_height),
            page_size - margin - half_height,
        )

        placements.append(
            (center_x, center_y, width, height, angle)
        )

    return placements
