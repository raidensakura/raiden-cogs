import logging, aiohttp

from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from .settings import GenshinSet
from .profile import GenshinProfile

log = logging.getLogger("red.raidensakura.genshinutils")


class GenshinUtils(GenshinSet, GenshinProfile, commands.Cog):
    """GenshinUtils commands."""

    __author__ = ["raidensakura"]
    __version__ = "1.0.0"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 243316261264556032, force_registration=True)
        default_global = {"schema_version": 1}
        default_user = {"UID": 000000000}
        self.config.register_global(**default_global)
        self.config.register_user(**default_user)
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Sinbad!"""
        pre_processed = super().format_help_for_context(ctx)
        s = "s" if len(self.__author__) > 1 else ""
        return f"{pre_processed}\n\nAuthor{s}: {', '.join(self.__author__)}\nCog Version: {self.__version__}"

    async def red_delete_data_for_user(self, **kwargs) -> None:
        """Nothing to delete"""
        return

    @commands.group()
    @commands.guild_only()
    async def genshin(self, ctx: commands.Context):
        """GenshinUtils main command."""
