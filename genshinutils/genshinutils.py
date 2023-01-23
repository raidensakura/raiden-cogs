import asyncio
import logging
from typing import Union

import discord
import genshin
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.commands import Context

log = logging.getLogger("red.raidensakura.genshinutils")


class GenshinUtils(commands.Cog):
    """
    A Genshin Impact cog.
    """

    __author__ = ["raidensakura"]
    __version__ = "1.0.0"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 243316261264556032, force_registration=True)
        default_global = {"schema_version": 1}
        default_user = {"UID": 000000000}
        self.config.register_user(**default_user)

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """
        Thanks Sinbad!
        """
        pre_processed = super().format_help_for_context(ctx)
        s = "s" if len(self.__author__) > 1 else ""
        return f"{pre_processed}\n\nAuthor{s}: {', '.join(self.__author__)}\nCog Version: {self.__version__}"

    async def red_delete_data_for_user(self, **kwargs) -> None:
        """Nothing to delete"""
        return

    @checks.is_owner()
    @commands.group()
    async def genshinset(self, ctx: commands.Context):
        """
        Settings for GenshinUtils cog.
        """

    @genshinset.command()
    async def ltoken(self, ctx: commands.Context):
        """Instructions on how to set the `ltoken` secret."""
        msg = f"Use `{ctx.prefix}set api genshinutils ltoken your_ltoken_here`."
        await ctx.send(msg)

    @genshinset.command()
    async def ltuid(self, ctx: commands.Context):
        """Instructions on how to set the `ltuid` secret."""
        msg = f"Use `{ctx.prefix}set api genshinutils ltuid your_ltuid_here`."
        await ctx.send(msg)

    @commands.group()
    async def genshin(self, ctx: commands.Context):
        """
        GenshinUtils main command.
        """

    @genshin.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(2, 5, commands.BucketType.member)
    async def profile(self, ctx: Context, *, member: Union[discord.Member, str, None]):
        """
        Display a Genshin Impact profile.
        If a UID is provided, it will display data for that player.
        If a Discord user is provided, it will display data for that user (if a Genshin UID is linked).
        If no argument is provided, it will display data for your account (if a Genshin UID is linked).
        """

        api_keys = await self.bot.get_shared_api_tokens("hoyolab")
        if api_keys.get("ltuid") is None or api_keys.get("ltoken") is None:
            return await ctx.send(f"API keys not set.")

        cookies = {"ltuid": api_keys.get("ltuid"), "ltoken": api_keys.get("ltoken")}

        client = genshin.Client(cookies)

        if not member:
            log.debug("Fetch own UID from config")
            uid = None
            return await ctx.send("todo")

        elif isinstance(member, discord.Member) and member.id != ctx.me.id:
            log.debug("Fetch mentioned user's UID from config")
            uid = None
            return await ctx.send("todo")

        elif isinstance(member, discord.Member) and member.id == ctx.me.id:
            return await ctx.send(f"Sorry, but I do not play Genshin.")

        elif isinstance(member, str) and len(member) == 9 and member.isdigit():
            uid = member
            try:
                data = await client.get_genshin_user(uid)
            except Exception as exc:
                log.exception("Error trying to fetch data from API.", exc_info=exc)
                return await ctx.send(
                    "Oops, I encountered an error while trying to fetch data from Hoyolab."
                )

            e = discord.Embed(
                color=(await ctx.embed_colour()),
                title=f"Data for {data.info.nickname} (AR{data.info.level})",
            )
            e.add_field(name="Achievements", value=data.stats.achievements, inline=True)
            e.add_field(name="Days Active", value=data.stats.days_active, inline=True)
            e.add_field(
                name="Characters Unlocked", value=data.stats.characters, inline=True
            )
            e.add_field(
                name="Highest Spiral Abyss Climb",
                value=data.stats.spiral_abyss,
                inline=True,
            )
            e.add_field(
                name="Oculi Collected",
                value=(
                    f"Anemoculi: {data.stats.anemoculi}\n"
                    f"Geoculi: {data.stats.geoculi}\n"
                    f"Electroculi: {data.stats.electroculi}\n"
                    f"Dendroculi: {data.stats.dendroculi}"
                ),
                inline=True,
            )

            try:
                return await ctx.send(embed=e)
            except Exception as exc:
                log.exception("Error trying to send choose embed.", exc_info=exc)
                return await ctx.send(
                    "Oops, I encountered an error while trying to send the embed."
                )
