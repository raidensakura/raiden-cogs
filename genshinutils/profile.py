import logging
from typing import Union

import discord
import genshin as genshinpy
from redbot.core import commands
from redbot.core.commands import Context

log = logging.getLogger("red.raidensakura.genshinutils")


class GenshinProfile(commands.Cog):
    """GenshinUtils profile commands."""

    # This will get replaced by genshinutils.py's `genshin`
    # Thanks Jojo#7791!
    @commands.group()
    @commands.guild_only()
    async def genshin(self, ctx: commands.Context):
        """GenshinUtils main command."""

    @genshin.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(2, 5, commands.BucketType.member)
    async def profile(self, ctx: Context, *, user_or_uid: Union[discord.Member, str, None]):
        """
        Display a Genshin Impact profile.
        If a UID is provided, it will display data for that UID.
        If a Discord user is provided, it will display data for that user (if UID is linked).
        If no argument is provided, it will display data for your account (if UID is linked).
        """

        api_keys = await self.bot.get_shared_api_tokens("hoyolab")
        if api_keys.get("ltuid") is None or api_keys.get("ltoken") is None:
            return await ctx.send(f"API keys not set.")

        cookies = {"ltuid": api_keys.get("ltuid"), "ltoken": api_keys.get("ltoken")}

        client = genshinpy.Client(cookies)

        async def get_profile(uid):
            try:
                data = await client.get_genshin_user(uid)
            except Exception as exc:
                log.debug("Error trying to fetch profile data from Hoyolab API.")
                return await ctx.send("No profile was found with that UID.")

            e = discord.Embed(
                color=(await ctx.embed_colour()),
                description=(
                    f"```fix\n" \
                    f"✨ :: Profile for {data.info.nickname} [AR {data.info.level}]```"
                    ),
                )
            e.set_thumbnail(url=data.characters[0].icon)
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
                name="Total Oculi Collected",
                value=(f"{data.stats.anemoculi + data.stats.geoculi + data.stats.electroculi + data.stats.dendroculi}"),
                inline=True,
            )
            e.add_field(
                name="Waypoints Unlocked",
                value=(f"{data.stats.unlocked_waypoints}"),
                inline=True
            )
            e.add_field(
                name="Total Chests Opened",
                value=(f"{data.stats.common_chests + data.stats.precious_chests + data.stats.exquisite_chests + data.stats.luxurious_chests + data.stats.remarkable_chests}"),
                inline=True
            )
            e.add_field(
                name="Domains Unlocked",
                value=(f"{data.stats.unlocked_domains}"),
                inline=True
            )

            try:
                return await ctx.send(embed=e)
            except Exception as exc:
                log.exception("Error trying to send embed.", exc_info=exc)
                return await ctx.send(
                    "Oops, I encountered an error while trying to send the embed."
                )

        if not user_or_uid:
            uid = await self.config.user(ctx.author).get_raw("UID")
            if not uid or uid == "000000000":
                return await ctx.send("You don't have any UID linked.")
            async with ctx.typing():
                return await get_profile(uid)

        elif isinstance(user_or_uid, discord.Member) and user_or_uid.id != ctx.me.id:
            uid = await self.config.user(user_or_uid).get_raw("UID")
            if not uid or uid == "000000000":
                return await ctx.send("That user has not linked a UID yet.")
            async with ctx.typing():
                return await get_profile(uid)

        elif isinstance(user_or_uid, discord.Member) and user_or_uid.id == ctx.me.id:
            return await ctx.send(f"Sorry, but I do not play Genshin.")

        elif isinstance(user_or_uid, str) and len(user_or_uid) == 9 and user_or_uid.isdigit():
            uid = user_or_uid
            async with ctx.typing():
                return await get_profile(uid)
