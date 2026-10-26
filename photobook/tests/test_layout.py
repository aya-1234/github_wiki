from pathlib import Path

import pytest
import math

from photobook.layout import build_random_placements, build_pages



def test_single_mode_preserves_one_photo_per_page() -> None:
    images = [Path(f"photo{i}.jpg") for i in range(5)]

    pages = build_pages(images)

    assert len(pages) == 5
    assert all(len(page.image_paths) == 1 for page in pages)


def test_collage_mode_splits_photos_into_pages() -> None:
    images = [Path(f"photo{i}.jpg") for i in range(10)]

    pages = build_pages(images, mode="collage", max_photos_per_page=4)

    assert [len(page.image_paths) for page in pages] == [4, 4, 2]
    assert [
        path
        for page in pages
        for path in page.image_paths
    ] == images


def test_collage_mode_handles_one_photo() -> None:
    image = Path("photo.jpg")

    pages = build_pages([image], mode="collage")

    assert len(pages) == 1
    assert pages[0].image_paths == (image,)


@pytest.mark.parametrize("mode", ["invalid", "", None])
def test_invalid_mode_is_rejected(mode: str) -> None:
    with pytest.raises(ValueError):
        build_pages([], mode=mode)  # type: ignore[arg-type]


@pytest.mark.parametrize("count", [0, 5, -1, True, 2.5])
def test_invalid_max_photos_per_page_is_rejected(count: int) -> None:
    with pytest.raises(ValueError):
        build_pages([], mode="collage", max_photos_per_page=count)

def test_random_placements_are_reproducible():
    first = build_random_placements(
        count=4,
        page_size=595,
        margin=34,
        seed=42,
    )
    second = build_random_placements(
        count=4,
        page_size=595,
        margin=34,
        seed=42,
    )

    assert first == second


def test_random_placements_change_with_seed():
    first = build_random_placements(
        count=4,
        page_size=595,
        margin=34,
        seed=42,
    )
    second = build_random_placements(
        count=4,
        page_size=595,
        margin=34,
        seed=43,
    )

    assert first != second


def test_random_placements_stay_inside_page():
    page_size = 595
    margin = 34

    placements = build_random_placements(
        count=4,
        page_size=page_size,
        margin=margin,
        seed=42,
    )

    for center_x, center_y, width, height, angle in placements:
        radians = math.radians(angle)
        half_width = (
            abs(width * math.cos(radians))
            + abs(height * math.sin(radians))
        ) / 2
        half_height = (
            abs(width * math.sin(radians))
            + abs(height * math.cos(radians))
        ) / 2

        assert center_x - half_width >= margin
        assert center_x + half_width <= page_size - margin
        assert center_y - half_height >= margin
        assert center_y + half_height <= page_size - margin


def test_random_placements_reject_invalid_count():
    import pytest

    with pytest.raises(ValueError):
        build_random_placements(
            count=5,
            page_size=595,
            margin=34,
            seed=42,
        )
