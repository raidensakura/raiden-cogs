from __future__ import annotations

from pathlib import Path

from PIL import Image

from . import _artcard

BACKGROUND_PATH = Path(__file__).parent.parent / "backgrounds" / "fangyi.jpg"
BORDER_COLOR = (123, 171, 145)  # sampled from the backdrop art's dominant green tones


def render(**kwargs) -> Image.Image:
    return _artcard.render(
        background_path=BACKGROUND_PATH, border_color=BORDER_COLOR, **kwargs
    )
