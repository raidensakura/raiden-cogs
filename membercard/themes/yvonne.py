from __future__ import annotations

from pathlib import Path

from PIL import Image

from . import _artcard

BACKGROUND_PATH = Path(__file__).parent.parent / "backgrounds" / "yvonne.jpg"
BORDER_COLOR = (234, 144, 192)  # sampled from the backdrop art's dominant pink tones


def render(**kwargs) -> Image.Image:
    return _artcard.render(
        background_path=BACKGROUND_PATH, border_color=BORDER_COLOR, **kwargs
    )
