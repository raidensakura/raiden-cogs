from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from . import _shared as s

PANEL_LEFT = 44
PANEL_WIDTH = 420
BOX_FILL = (10, 11, 16, 140)
BOX_BORDER = (255, 255, 255, 45)

_background_cache: dict[Path, Image.Image] = {}
_vignette: Image.Image | None = None


def _load_background(path: Path) -> Image.Image:
    """Returns a cached, preprocessed static backdrop.

    Blur, tinting, and the vignette only depend on the selected bundled artwork;
    caching their composited result avoids repeating several full-card pixel passes.
    """
    if path not in _background_cache:
        img = Image.open(path).convert("RGB")
        iw, ih = img.size
        scale = max(s.WIDTH / iw, s.HEIGHT / ih) * 1.08
        img = img.resize((max(1, int(iw * scale)), max(1, int(ih * scale))))
        left = (img.width - s.WIDTH) // 2
        top = (img.height - s.HEIGHT) // 2
        img = img.crop((left, top, left + s.WIDTH, top + s.HEIGHT))
        img = img.filter(ImageFilter.GaussianBlur(1.5))
        img = Image.blend(img, Image.new("RGB", (s.WIDTH, s.HEIGHT), (18, 9, 11)), 0.16)
        card = img.convert("RGBA")
        card.putalpha(255)
        card.paste((12, 7, 8), (0, 0, s.WIDTH, s.HEIGHT), _get_vignette())
        _background_cache[path] = card
    return _background_cache[path].copy()


def _get_vignette() -> Image.Image:
    global _vignette
    if _vignette is None:
        grad_cols, grad_rows = 64, 40
        max_dist = 780
        small_grad = Image.new("L", (grad_cols, grad_rows), 0)
        for gy in range(grad_rows):
            y = gy * s.HEIGHT / (grad_rows - 1)
            for gx in range(grad_cols):
                x = gx * s.WIDTH / (grad_cols - 1)
                dist = (x * x + y * y) ** 0.5
                small_grad.putpixel((gx, gy), int(175 * max(0.0, 1 - dist / max_dist)))
        _vignette = small_grad.resize((s.WIDTH, s.HEIGHT), Image.Resampling.BILINEAR)
    return _vignette


def render(
    *,
    background_path: Path,
    border_color: tuple[int, int, int],
    display_name: str,
    username: str,
    avatar_bytes: bytes,
    guild_name: str,
    guild_icon_bytes: bytes | None,
    joined_at: datetime | None,
    roles: list[tuple[str, tuple[int, int, int]]],
    user_id: int,
    created_at: datetime | None = None,
    permission_tier: str = "Member",
    is_boosting: bool = False,
    status_text: str | None = None,
    **_unused,
) -> Image.Image:
    """Draws a full-art profile card over a fixed backdrop image."""

    # Bullet markers and the top-role tag use the theme's own border_color rather
    # than the member's role color, so they stay consistent with each theme's art
    # instead of occasionally clashing with it (or falling back to Discord blurple).

    # Backdrop: bundled artwork, lightly softened with a warm tint for legibility.
    card = _load_background(background_path)

    panel_top = 210

    # Stat panel (left) and quote box (right): both drawn as clearly-bounded translucent
    # panels rather than one full-bleed gradient, so most of the art stays fully visible.
    # Built on their own transparent layer and alpha composited, since ImageDraw fills
    # overwrite pixels rather than blending them.
    stat_x1, stat_y1 = 20, panel_top
    stat_x2, stat_y2 = 504, s.HEIGHT - 20
    box_x1, box_y1 = 536, panel_top
    box_x2, box_y2 = s.WIDTH - 20, 430
    server_x1, server_y1 = box_x1, box_y2 + 20
    server_x2, server_y2 = box_x2, stat_y2

    translucent = Image.new("RGBA", (s.WIDTH, s.HEIGHT), (0, 0, 0, 0))
    translucent_draw = ImageDraw.Draw(translucent)

    translucent_draw.rounded_rectangle(
        [stat_x1, stat_y1, stat_x2, stat_y2], radius=20, fill=(10, 6, 7, 165)
    )
    translucent_draw.rounded_rectangle(
        [stat_x1, stat_y1, stat_x2, stat_y2], radius=20, outline=BOX_BORDER, width=2
    )
    translucent_draw.rounded_rectangle(
        [box_x1, box_y1, box_x2, box_y2], radius=18, fill=BOX_FILL
    )
    translucent_draw.rounded_rectangle(
        [box_x1, box_y1, box_x2, box_y2], radius=18, outline=BOX_BORDER, width=2
    )
    quote_font = s.font(s.FONT_CONDENSED_BOLD, 70)
    translucent_draw.text(
        (box_x1 + 20, box_y1 - 4), "“", font=quote_font, fill=(255, 255, 255, 60)
    )
    translucent_draw.rounded_rectangle(
        [server_x1, server_y1, server_x2, server_y2], radius=18, fill=BOX_FILL
    )
    translucent_draw.rounded_rectangle(
        [server_x1, server_y1, server_x2, server_y2],
        radius=18,
        outline=BOX_BORDER,
        width=2,
    )

    card = Image.alpha_composite(card, translucent)
    draw = ImageDraw.Draw(card, "RGBA")

    # Avatar, top-left, crisp with a thin accent ring
    avatar_size = 140
    avatar_pos = (44, 40)
    ring_pad = 5
    draw.ellipse(
        [
            avatar_pos[0] - ring_pad,
            avatar_pos[1] - ring_pad,
            avatar_pos[0] + avatar_size + ring_pad,
            avatar_pos[1] + avatar_size + ring_pad,
        ],
        outline=border_color,
        width=4,
    )
    avatar = s.fit_image(avatar_bytes, (avatar_size, avatar_size))
    avatar.putalpha(s.circle_mask((avatar_size, avatar_size)))
    card.paste(avatar, avatar_pos, avatar)

    text_x = avatar_pos[0] + avatar_size + 30

    name_font = s.font(s.FONT_BOLD, 57)
    name_text = s.truncate(draw, display_name, name_font, s.WIDTH - 40 - text_x)
    draw.text((text_x + 3, 46), name_text, font=name_font, fill=(0, 0, 0, 170))
    draw.text((text_x, 43), name_text, font=name_font, fill=s.WHITE)

    top_role_name = roles[0][0] if roles else "Member"
    tag_font = s.font(s.FONT_SEMIBOLD, 22)
    tag_pad = 14
    tag_text = s.truncate(draw, top_role_name.upper(), tag_font, s.WIDTH - text_x - 60)
    tag_w = int(draw.textlength(tag_text, font=tag_font) + tag_pad * 2)
    tag_y = 118
    draw.rounded_rectangle(
        [text_x, tag_y, text_x + tag_w, tag_y + 34], radius=17, fill=border_color
    )
    draw.text(
        (text_x + tag_pad, tag_y + 3),
        tag_text,
        font=tag_font,
        fill=s.text_color_for_bg(border_color),
    )

    meta_font = s.font(s.FONT_REGULAR, 21)
    joined_text = joined_at.strftime("%Y.%m.%d") if joined_at else "Unknown"
    meta_text = f"MEMBER SINCE {joined_text}   •   ID {s.id_number(user_id)}"
    draw.text((text_x, 166), meta_text, font=meta_font, fill=(225, 226, 230))

    # Left stat column
    label_font = s.font(s.FONT_SEMIBOLD, 19)
    value_font = s.font(s.FONT_CONDENSED_BOLD, 40)

    row1_y = 258
    draw.rectangle(
        [PANEL_LEFT, row1_y + 4, PANEL_LEFT + 14, row1_y + 18], fill=border_color
    )
    draw.text(
        (PANEL_LEFT + 26, row1_y), "AUTHORITY LEVEL", font=label_font, fill=s.MUTED
    )
    draw.text((PANEL_LEFT, row1_y + 26), permission_tier, font=value_font, fill=s.WHITE)

    row2_y = row1_y + 92
    draw.rectangle(
        [PANEL_LEFT, row2_y + 4, PANEL_LEFT + 14, row2_y + 18], fill=border_color
    )
    draw.text((PANEL_LEFT + 26, row2_y), "ACCOUNT AGE", font=label_font, fill=s.MUTED)
    age_text = s.truncate(draw, s.account_age_text(created_at), value_font, PANEL_WIDTH)
    draw.text((PANEL_LEFT, row2_y + 26), age_text, font=value_font, fill=s.WHITE)

    # Three-column mini stat row. Tenure gets the most room since its text ("2 years
    # 30 days") runs much longer than the roles count or boost yes/no.
    mini_y = row2_y + 96
    mini_widths = [90, 240, 90]
    mini_font = s.font(s.FONT_CONDENSED_BOLD, 35)
    mini_label_font = s.font(s.FONT_SEMIBOLD, 15)
    tenure_days = (
        max(0, (datetime.now(timezone.utc) - joined_at).days) if joined_at else None
    )
    mini_stats = [
        (str(len(roles)), "ROLES"),
        (s.duration_text(tenure_days) if tenure_days is not None else "—", "TENURE"),
        ("YES" if is_boosting else "NO", "BOOST"),
    ]
    col_x = PANEL_LEFT
    for (value, label), col_w in zip(mini_stats, mini_widths):
        col_max_w = col_w - 10
        value_text = s.truncate(draw, value, mini_font, col_max_w)
        draw.text((col_x, mini_y), value_text, font=mini_font, fill=s.WHITE)
        draw.text((col_x, mini_y + 40), label, font=mini_label_font, fill=s.MUTED)
        col_x += col_w

    # Role chips
    chips_y = mini_y + 78
    chip_font = s.font(s.FONT_SEMIBOLD, 20)
    s.draw_role_chips(
        draw,
        roles,
        x=PANEL_LEFT,
        y=chips_y,
        max_right=PANEL_LEFT + PANEL_WIDTH,
        bottom_limit=s.HEIGHT - 40,
        chip_font=chip_font,
    )

    # Right side: status text, inside the quote box already drawn on the translucent layer
    status_font = s.font(s.FONT_REGULAR, 25)
    status_display = (
        status_text.strip() if status_text and status_text.strip() else None
    )
    inner_left = box_x1 + 36
    inner_width = (box_x2 - 28) - inner_left
    if status_display:
        lines = s.wrap_text(draw, status_display, status_font, inner_width, 3)
        text_color = s.WHITE
    else:
        lines = ["No status message set."]
        text_color = s.MUTED
    line_h = 32
    total_h = len(lines) * line_h
    start_y = box_y1 + (box_y2 - box_y1 - total_h) // 2
    for i, line in enumerate(lines):
        draw.text(
            (inner_left, start_y + i * line_h), line, font=status_font, fill=text_color
        )

    # Server identity section, below the status box (panel already drawn on the
    # translucent layer above; this just adds content on top of it). Split into two
    # aligned rows: icon + name/caption up top, a divider, then the barcode footer.
    server_pad = 24
    server_icon_size = 72
    server_icon_pos = (server_x1 + server_pad, server_y1 + 20)
    s.draw_guild_icon(
        card,
        draw,
        guild_icon_bytes,
        guild_name,
        server_icon_pos,
        server_icon_size,
        s.font(s.FONT_CONDENSED_BOLD, 37),
    )

    server_text_x = server_icon_pos[0] + server_icon_size + 22
    server_text_w = server_x2 - 20 - server_text_x

    server_name_font = s.font(s.FONT_CONDENSED_BOLD, 35)
    server_name_text = s.truncate(draw, guild_name, server_name_font, server_text_w)
    server_name_y = server_icon_pos[1] + 6
    draw.text(
        (server_text_x, server_name_y),
        server_name_text,
        font=server_name_font,
        fill=s.WHITE,
    )
    draw.text(
        (server_text_x, server_name_y + 36),
        "OFFICIAL MEMBER IDENTIFICATION",
        font=s.font(s.FONT_SEMIBOLD, 16),
        fill=s.MUTED,
    )

    divider_y = server_icon_pos[1] + server_icon_size + 16
    draw.line(
        [(server_x1 + server_pad, divider_y), (server_x2 - server_pad, divider_y)],
        fill=(255, 255, 255, 35),
        width=2,
    )

    # Footer: barcode + fake ID number, mirroring the classic theme's card footer.
    # The barcode is generated from the ID digest itself.
    barcode_y = divider_y + 18
    id_digest = s.id_number(user_id).replace("-", "")
    s.barcode(draw, server_x1 + server_pad, barcode_y, 22, id_digest)
    id_font = s.font(s.FONT_SEMIBOLD, 16)
    id_text = f"ID NO. {s.id_number(user_id)}"
    id_bbox = draw.textbbox((0, 0), id_text, font=id_font)
    id_w = id_bbox[2] - id_bbox[0]
    draw.text(
        (server_x2 - server_pad - id_w, barcode_y + 3),
        id_text,
        font=id_font,
        fill=s.MUTED,
    )

    # Outer frame: stroke's outer edge is inset to exactly meet the rounded-corner mask
    # applied below, so the border doesn't get clipped or leave a gap at the corners.
    s.draw_card_frame(draw, (s.WIDTH, s.HEIGHT), s.RADIUS, border_color, width=6)

    mask = s.rounded_mask((s.WIDTH, s.HEIGHT), s.RADIUS)
    card.putalpha(mask)

    return card
