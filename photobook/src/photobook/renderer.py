from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from photobook.layout import PhotoPage
from photobook.layout import PhotoPage, build_random_placements


def _normalized_image(path: Path) -> BytesIO:
    """Apply EXIF orientation and convert to an RGB JPEG held in memory."""
    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original)
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, "white")
            background.paste(rgba, mask=rgba.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")

        output = BytesIO()
        image.save(output, format="JPEG", quality=94, optimize=True)
        output.seek(0)
        return output


def _draw_contained_image(
    pdf: canvas.Canvas,
    path: Path,
    x: float,
    y: float,
    box_width: float,
    box_height: float,
) -> None:
    """Draw a complete image inside a box without cropping."""
    image_data = _normalized_image(path)
    try:
        reader = ImageReader(image_data)
        image_width, image_height = reader.getSize()

        scale = min(
            box_width / image_width,
            box_height / image_height,
        )
        draw_width = image_width * scale
        draw_height = image_height * scale

        draw_x = x + (box_width - draw_width) / 2
        draw_y = y + (box_height - draw_height) / 2

        pdf.drawImage(
            reader,
            draw_x,
            draw_y,
            width=draw_width,
            height=draw_height,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
    finally:
        image_data.close()

def _draw_photo_page(
    pdf: canvas.Canvas,
    page: PhotoPage,
    page_size: float,
    margin: float,
    gap: float,
    background: str,
    random_seed: int | None = None,
    random_layout: bool = True,
) -> None:
    """写真をランダムな位置・サイズ・角度で重ねて描画する。"""
    pdf.setFillColor(HexColor(background))
    pdf.rect(0, 0, page_size, page_size, stroke=0, fill=1)

    photos = page.image_paths

    if not random_layout:
        if len(photos) != 1:
            raise ValueError(
                "single モードでは1ページに写真1枚が必要です。"
            )

        _draw_contained_image(
            pdf,
            photos[0],
            margin,
            margin,
            page_size - 2 * margin,
            page_size - 2 * margin,
        )
        return

    placements = build_random_placements(
        count=len(photos),
        page_size=page_size,
        margin=margin,
        seed=random_seed,
    )

    for path, placement in zip(photos, placements, strict=True):
        center_x, center_y, box_width, box_height, angle = placement
        image_data = _normalized_image(path)

        try:
            reader = ImageReader(image_data)
            image_width, image_height = reader.getSize()

            # 元画像の縦横比を保ち、配置枠の中に収める。
            scale = min(
                box_width / image_width,
                box_height / image_height,
            )
            draw_width = image_width * scale
            draw_height = image_height * scale

            # 写真の中心を原点にして回転する。
            pdf.saveState()
            try:
                pdf.translate(center_x, center_y)
                pdf.rotate(angle)
                pdf.drawImage(
                    reader,
                    -draw_width / 2,
                    -draw_height / 2,
                    width=draw_width,
                    height=draw_height,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            finally:
                pdf.restoreState()
        finally:
            image_data.close()

def render_pdf(
    pages: list[PhotoPage],
    destination: Path,
    title: str,
    subtitle: str,
    page_size_mm: float = 210,
    margin_mm: float = 12,
    cover_background: str = "#F5F2EA",
    page_background: str = "#FFFFFF",
    title_color: str = "#202020",
    gap_mm: float = 4,
    random_seed: int | None = None,
    layout_mode: str = "single",
) -> None:
    """Render a minimalist cover and one image per square page."""
    from reportlab.lib.units import mm

    page_size = page_size_mm * mm
    margin = margin_mm * mm
    destination.parent.mkdir(parents=True, exist_ok=True)

    pdf = canvas.Canvas(
        str(destination),
        pagesize=(page_size, page_size),
        pageCompression=1,
        invariant=1,
    )
    pdf.setTitle(title or "Photobook")
    pdf.setAuthor("Photobook")

    # Cover: restrained typography with generous negative space.
    pdf.setFillColor(HexColor(cover_background))
    pdf.rect(0, 0, page_size, page_size, stroke=0, fill=1)
    pdf.setFillColor(HexColor(title_color))
    pdf.setFont("Helvetica", 26)
    pdf.drawString(margin, page_size * 0.56, title[:100] or "Photobook")
    if subtitle.strip():
        pdf.setFont("Helvetica", 10)
        pdf.drawString(margin, page_size * 0.56 - 22, subtitle[:160])
    pdf.setStrokeColor(HexColor(title_color))
    pdf.setLineWidth(0.5)
    pdf.line(margin, margin, margin + 28 * mm, margin)
    pdf.showPage()

    gap = gap_mm * mm

    for page_index, page in enumerate(pages):
        page_seed = (
            None if random_seed is None else random_seed + page_index
        )

        _draw_photo_page(
            pdf,
            page,
            page_size,
            margin,
            gap,
            page_background,
            random_seed=page_seed,
            random_layout=(layout_mode == "collage"),
        )
        pdf.showPage()

    pdf.save()
