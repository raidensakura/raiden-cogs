from __future__ import annotations

from pathlib import Path

from PIL import Image

from . import _artcard

BACKGROUND_PATH = Path(__file__).parent.parent / "backgrounds" / "laevatain.jpg"
BORDER_COLOR = (208, 82, 74)  # sampled from the backdrop art's dominant red tones


def render(**kwargs) -> Image.Image:
    return _artcard.render(
        background_path=BACKGROUND_PATH, border_color=BORDER_COLOR, **kwargs
    )
