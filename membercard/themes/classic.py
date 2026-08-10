from __future__ import annotations

from datetime import datetime

from PIL import Image, ImageDraw

from . import _shared as s

BG_TOP = (22, 24, 32)
BG_BOTTOM = (33, 36, 48)
DIVIDER = (68, 72, 88)


def render(
    *,
    display_name: str,
    username: str,
    avatar_bytes: bytes,
    guild_name: str,
    guild_icon_bytes: bytes | None,
    roles: list[tuple[str, tuple[int, int, int]]],
    user_id: int,
    accent: tuple[int, int, int] | None,
    created_at: datetime | None = None,
    **_unused,
) -> Image.Image:
    """Draws an ID-card style membership card at its working resolution."""

    accent_rgb = accent if accent and any(accent) else s.DEFAULT_ACCENT

    card = Image.new("RGBA", (s.WIDTH, s.HEIGHT), (0, 0, 0, 255))
    draw = ImageDraw.Draw(card)

    for row in range(s.HEIGHT):
        ratio = row / s.HEIGHT
        color = tuple(
            int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * ratio) for i in range(3)
        )
        draw.line([(0, row), (s.WIDTH, row)], fill=color)

    draw.rectangle([0, 0, s.WIDTH, 12], fill=accent_rgb)
    draw.rectangle([0, s.HEIGHT - 12, s.WIDTH, s.HEIGHT], fill=accent_rgb)

    # Punch hole, top-right, common on real ID badges. Drawn supersampled since
    # Pillow's ellipse rendering isn't anti-aliased and looks lopsided at this size.
    s.draw_ring(
        card, (s.WIDTH - 50, 42), outer_radius=13, inner_radius=10, color=DIVIDER
    )

    header_y = 40
    icon_size = 68
    s.draw_guild_icon(
        card,
        draw,
        guild_icon_bytes,
        guild_name,
        (40, header_y),
        icon_size,
        s.font(s.FONT_CONDENSED_BOLD, 37),
    )
    text_x = 40 + icon_size + 20

    guild_font = s.font(s.FONT_CONDENSED_BOLD, 35)
    guild_label = s.truncate(draw, guild_name, guild_font, s.WIDTH - text_x - 100)
    draw.text((text_x, header_y - 2), guild_label, font=guild_font, fill=s.WHITE)
    draw.text(
        (text_x, header_y + 34),
        "OFFICIAL MEMBER IDENTIFICATION",
        font=s.font(s.FONT_SEMIBOLD, 16),
        fill=s.MUTED,
    )

    draw.line([(40, 132), (s.WIDTH - 40, 132)], fill=DIVIDER, width=2)

    # Avatar with accent-colored frame
    avatar_size = 260
    avatar_pos = (48, 168)
    frame_pad = 6
    draw.rounded_rectangle(
        [
            avatar_pos[0] - frame_pad,
            avatar_pos[1] - frame_pad,
            avatar_pos[0] + avatar_size + frame_pad,
            avatar_pos[1] + avatar_size + frame_pad,
        ],
        radius=24,
        fill=accent_rgb,
    )
    avatar = s.fit_image(avatar_bytes, (avatar_size, avatar_size))
    avatar.putalpha(s.rounded_mask((avatar_size, avatar_size), 18))
    card.paste(avatar, avatar_pos, avatar)

    info_x = avatar_pos[0] + avatar_size + 50
    info_width = s.WIDTH - 40 - info_x

    name_font = s.font(s.FONT_CONDENSED_BOLD, 64)
    name_text = s.truncate(draw, display_name, name_font, info_width)
    draw.text((info_x, 172), name_text, font=name_font, fill=s.WHITE)

    handle_font = s.font(s.FONT_REGULAR, 29)
    handle_text = s.truncate(draw, f"@{username}", handle_font, info_width)
    draw.text((info_x, 240), handle_text, font=handle_font, fill=accent_rgb)

    draw.line(
        [(info_x, 290), (info_x + info_width, 290)],
        fill=DIVIDER,
        width=2,
    )

    label_font = s.font(s.FONT_SEMIBOLD, 18)
    value_font = s.font(s.FONT_CONDENSED_BOLD, 28)

    col_gap = 40
    col_width = (info_width - col_gap) // 2
    col1_x = info_x
    col2_x = info_x + col_width + col_gap

    draw.text((col1_x, 312), "ACCOUNT AGE", font=label_font, fill=s.MUTED)
    age_text = s.truncate(draw, s.account_age_text(created_at), value_font, col_width)
    draw.text((col1_x, 336), age_text, font=value_font, fill=s.WHITE)

    draw.text((col2_x, 312), "ACCOUNT CREATED", font=label_font, fill=s.MUTED)
    created_text = created_at.strftime("%B %d, %Y") if created_at else "Unknown"
    created_text = s.truncate(draw, created_text, value_font, col_width)
    draw.text((col2_x, 336), created_text, font=value_font, fill=s.WHITE)

    draw.text((info_x, 392), "ROLES", font=label_font, fill=s.MUTED)

    chip_font = s.font(s.FONT_SEMIBOLD, 21)
    s.draw_role_chips(
        draw,
        roles,
        x=info_x,
        y=418,
        max_right=info_x + info_width,
        bottom_limit=s.HEIGHT - 100,
        chip_font=chip_font,
    )

    # Footer: barcode + fake ID number, the barcode generated from the ID digest itself
    footer_y = s.HEIGHT - 76
    draw.line(
        [(40, footer_y - 20), (s.WIDTH - 40, footer_y - 20)], fill=DIVIDER, width=2
    )
    id_digest = s.id_number(user_id).replace("-", "")
    s.barcode(draw, 48, footer_y, 40, id_digest)

    id_font = s.font(s.FONT_SEMIBOLD, 20)
    id_text = f"ID NO. {s.id_number(user_id)}"
    id_bbox = draw.textbbox((0, 0), id_text, font=id_font)
    id_w = id_bbox[2] - id_bbox[0]
    draw.text((s.WIDTH - 48 - id_w, footer_y + 4), id_text, font=id_font, fill=s.MUTED)

    mask = s.rounded_mask((s.WIDTH, s.HEIGHT), s.RADIUS)
    card.putalpha(mask)

    return card
