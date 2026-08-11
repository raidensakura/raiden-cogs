from __future__ import annotations

from pathlib import Path

from PIL import Image

from . import _artcard

BACKGROUND_PATH = Path(__file__).parent.parent / "backgrounds" / "perlica.jpg"
# Dominant non-neutral hue sampled from Perlica's bundled backdrop artwork.
BORDER_COLOR = (122, 168, 194)


def render(**kwargs) -> Image.Image:
    return _artcard.render(
        background_path=BACKGROUND_PATH, border_color=BORDER_COLOR, **kwargs
    )
