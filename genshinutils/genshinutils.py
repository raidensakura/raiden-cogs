import logging
from typing import Literal

from enkanetwork import EnkaNetworkAPI
from redbot.core import Config, commands

from .daily import GenshinDaily
from .notes import GenshinNotes
from .profile import GenshinProfile
from .register import GenshinRegister
from .settings import GenshinSet

enka_client = EnkaNetworkAPI()

log = logging.getLogger("red.raidensakura.genshinutils")


class GenshinUtils(
    GenshinSet,
    GenshinRegister,
    GenshinProfile,
    GenshinNotes,
    GenshinDaily,
    commands.Cog,
):
    """GenshinUtils commands."""

    __author__ = ["raidensakura"]
    __version__ = "1.0.0"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 243316261264556032, force_registration=True)
        default_global = {
            "schema_version": 1,
            "verification": True,
            "encryption_key": "",
        }
        default_user = {"UID": "", "ltuid": "", "ltoken": ""}
        self.config.register_global(**default_global)
        self.config.register_user(**default_user)
        self.enka_client = enka_client

    def cog_unload(self):
        enka_client._close()

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Sinbad!"""
        pre_processed = super().format_help_for_context(ctx)
        s = "s" if len(self.__author__) > 1 else ""
        return f"{pre_processed}\n\nAuthor{s}: {', '.join(self.__author__)}\nCog Version: {self.__version__}"

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user_strict", "user"],
        user_id: int,
    ):
        await self.config.user_from_id(user_id).clear()

    @commands.group()
    async def genshin(self, ctx: commands.Context):
        """GenshinUtils main command."""
        # TODO: Embed explaining what this cog does and its info
