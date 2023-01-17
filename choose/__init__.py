import contextlib
import importlib
import json
from pathlib import Path

from redbot.core import VersionInfo
from redbot.core.bot import Red

from .choose import BetterChoose

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red) -> None:
    global old_choose
    old_choose = bot.get_command("choose")
    if old_choose:
        bot.remove_command(old_choose.name)

    cog = BetterChoose(bot)

    r = bot.add_cog(cog)
    if r is not None:
        await r
