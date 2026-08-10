from __future__ import annotations

import hashlib
import io
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(__file__).parent.parent / "fonts"

FONT_CONDENSED_BOLD = FONT_DIR / "BarlowCondensed-Bold.ttf"
FONT_CONDENSED_SEMIBOLD = FONT_DIR / "BarlowCondensed-SemiBold.ttf"
FONT_REGULAR = FONT_DIR / "Barlow-Regular.ttf"
FONT_SEMIBOLD = FONT_DIR / "Barlow-SemiBold.ttf"
FONT_BOLD = FONT_DIR / "Barlow-Bold.ttf"

WIDTH = 1050
HEIGHT = 650
RADIUS = 32

MUTED = (150, 155, 168)
WHITE = (240, 241, 245)
DEFAULT_ACCENT = (88, 101, 242)  # discord blurple
CHIP_DEFAULT = (60, 64, 78)

_font_cache: dict[tuple[Path, int], ImageFont.FreeTypeFont] = {}


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(str(path), size)
    return _font_cache[key]


def text_color_for_bg(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    r, g, b = rgb
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return (25, 25, 28) if luminance > 150 else (245, 245, 248)


@lru_cache(maxsize=16)
def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255
    )
    return mask


@lru_cache(maxsize=16)
def circle_mask(size: tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size[0] - 1, size[1] - 1], fill=255)
    return mask


def fit_image(raw: bytes, size: tuple[int, int]) -> Image.Image:
    """Scales and center-crops an image to exactly fill the given size."""
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    w, h = img.size
    scale = max(size[0] / w, size[1] / h)
    img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
    left = (img.width - size[0]) // 2
    top = (img.height - size[1]) // 2
    return img.crop((left, top, left + size[0], top + size[1]))


def truncate(draw: ImageDraw.ImageDraw, text: str, font_obj, max_width: int) -> str:
    if draw.textlength(text, font=font_obj) <= max_width:
        return text
    ellipsis = "…"
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if draw.textlength(text[:middle] + ellipsis, font=font_obj) <= max_width:
            low = middle
        else:
            high = middle - 1
    return text[:low] + ellipsis if low else ellipsis


def id_number(user_id: int) -> str:
    digest = hashlib.sha256(str(user_id).encode()).hexdigest().upper()
    return f"{digest[:4]}-{digest[4:8]}-{digest[8:12]}"


def duration_text(days: int) -> str:
    years, days = divmod(days, 365)
    parts = []
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    parts.append(f"{days} day{'s' if days != 1 else ''}")
    return " ".join(parts)


def account_age_text(created_at: datetime | None) -> str:
    if created_at is None:
        return "Unknown"
    days = max(0, (datetime.now(timezone.utc) - created_at).days)
    return duration_text(days)


def barcode(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    height: int,
    digest: str,
    color: tuple[int, int, int] = WHITE,
) -> int:
    """Draws one bar (and trailing gap) per hex character of digest, so the pattern
    is directly derived from the ID number shown alongside it. Pass the same digest
    used to build that ID number (id_number(user_id).replace("-", "")) so the two
    stay visually tied to each other."""
    cursor = x
    for char in digest:
        value = int(char, 16)
        bar_width = 3 + (value % 5) * 2
        gap = 3 + (value // 5) * 2
        draw.rectangle([cursor, y, cursor + bar_width, y + height], fill=color)
        cursor += bar_width + gap
    return cursor


def wrap_text(
    draw: ImageDraw.ImageDraw, text: str, font_obj, max_width: int, max_lines: int
) -> list[str]:
    """Greedily wraps text to at most max_lines, ellipsizing the last line on overflow."""
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textlength(candidate, font=font_obj) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        ellipsis = "…"
        while last and draw.textlength(last + ellipsis, font=font_obj) > max_width:
            last = last[:-1]
        lines[-1] = (last + ellipsis) if last else ellipsis
    return lines


def draw_ring(
    card: Image.Image,
    center: tuple[int, int],
    outer_radius: int,
    inner_radius: int,
    color: tuple[int, int, int],
    supersample: int = 4,
) -> None:
    """Draws an anti-aliased ring (annulus) onto card, pasted via its own alpha so the
    background shows through the hole. Avoids Pillow's uneven thick-outline rendering
    on small ellipses by drawing oversized then downscaling with a smoothing filter."""
    size = outer_radius * 2 * supersample
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(layer)
    layer_draw.ellipse([0, 0, size - 1, size - 1], fill=(*color, 255))
    inset = (outer_radius - inner_radius) * supersample
    layer_draw.ellipse(
        [inset, inset, size - 1 - inset, size - 1 - inset], fill=(0, 0, 0, 0)
    )
    layer = layer.resize((outer_radius * 2, outer_radius * 2), Image.Resampling.LANCZOS)
    card.paste(layer, (center[0] - outer_radius, center[1] - outer_radius), layer)


def draw_guild_icon(
    card: Image.Image,
    draw: ImageDraw.ImageDraw,
    guild_icon_bytes: bytes | None,
    guild_name: str,
    pos: tuple[int, int],
    size: int,
    fallback_font,
    fallback_fill: tuple[int, int, int] = CHIP_DEFAULT,
    text_fill: tuple[int, int, int] = WHITE,
) -> None:
    """Draws a circular guild icon at pos, falling back to an initial-letter badge."""
    x, y = pos
    if guild_icon_bytes:
        icon = fit_image(guild_icon_bytes, (size, size))
        icon.putalpha(circle_mask((size, size)))
        card.paste(icon, (x, y), icon)
        return

    draw.ellipse([x, y, x + size, y + size], fill=fallback_fill)
    initial = guild_name[:1].upper() if guild_name else "?"
    bbox = draw.textbbox((0, 0), initial, font=fallback_font)
    draw.text(
        (
            x + size / 2 - (bbox[2] - bbox[0]) / 2,
            y + size / 2 - (bbox[3] - bbox[1]) / 2 - bbox[1],
        ),
        initial,
        font=fallback_font,
        fill=text_fill,
    )


def draw_card_frame(
    draw: ImageDraw.ImageDraw,
    size: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
    width: int,
) -> None:
    """Draws a border stroke whose outer edge exactly coincides with the rounded-corner
    alpha mask applied to the card, so the two don't visibly mismatch at the corners."""
    inset = width / 2
    draw.rounded_rectangle(
        [inset, inset, size[0] - 1 - inset, size[1] - 1 - inset],
        radius=radius - inset,
        outline=color,
        width=width,
    )


def draw_role_chips(
    draw: ImageDraw.ImageDraw,
    roles: list[tuple[str, tuple[int, int, int]]],
    *,
    x: int,
    y: int,
    max_right: int,
    bottom_limit: int,
    chip_font,
    empty_text: str = "No roles assigned",
    empty_color: tuple[int, int, int] = MUTED,
) -> None:
    """Draws wrapping, pill-shaped role chips, capping overflow with a '+N more' chip."""
    chip_x, chip_y = x, y
    chip_h = 32
    shown = 0

    if not roles:
        draw.text((chip_x, chip_y + 4), empty_text, font=chip_font, fill=empty_color)
        return

    for name, color in roles:
        pad_x = 14
        text_w = draw.textlength(name, font=chip_font)
        chip_w = int(text_w + pad_x * 2)
        if chip_x + chip_w > max_right:
            chip_x = x
            chip_y += chip_h + 10
        if chip_y + chip_h > bottom_limit:
            remaining = len(roles) - shown
            more_text = f"+{remaining} more"
            more_w = int(draw.textlength(more_text, font=chip_font) + pad_x * 2)
            draw.rounded_rectangle(
                [chip_x, chip_y, chip_x + more_w, chip_y + chip_h],
                radius=chip_h // 2,
                fill=CHIP_DEFAULT,
            )
            draw.text(
                (chip_x + pad_x, chip_y + 5), more_text, font=chip_font, fill=WHITE
            )
            return
        fill = color if any(color) else CHIP_DEFAULT
        draw.rounded_rectangle(
            [chip_x, chip_y, chip_x + chip_w, chip_y + chip_h],
            radius=chip_h // 2,
            fill=fill,
        )
        draw.text(
            (chip_x + pad_x, chip_y + 5),
            name,
            font=chip_font,
            fill=text_color_for_bg(fill),
        )
        chip_x += chip_w + 10
        shown += 1
