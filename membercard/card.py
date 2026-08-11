from __future__ import annotations

import io

from PIL import Image

from .themes import classic, fangyi, laevatain, perlica, yvonne

DEFAULT_THEME = "classic"

THEMES = {
    "classic": classic.render,
    "laevatain": laevatain.render,
    "fangyi": fangyi.render,
    "yvonne": yvonne.render,
    "perlica": perlica.render,
}

# Themes draw at a higher internal resolution than this; downscaling to it with a
# high-quality filter both anti-aliases the vector edges (Pillow's basic shape drawing
# isn't anti-aliased on its own) and keeps the exported PNG close to what Discord
# actually renders it at, avoiding a second, blurrier client-side downscale.
EXPORT_WIDTH = 800


def render_card(*, theme: str = DEFAULT_THEME, **kwargs) -> io.BytesIO:
    """Render a card at its final Discord display size.

    Theme renderers return their working image directly.  This deliberately keeps
    PNG encoding to one pass, instead of encoding a high-resolution image only to
    decode it again for the export resize.
    """
    renderer = THEMES.get(theme, THEMES[DEFAULT_THEME])
    img = renderer(**kwargs)
    export_height = round(EXPORT_WIDTH * img.height / img.width)
    img = img.resize((EXPORT_WIDTH, export_height), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output
