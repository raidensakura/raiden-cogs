import logging
from typing import Union

import genshin

import discord
from time import mktime
from redbot.core import checks, commands

from .utils import validate_uid, get_user_cookie, generate_embed

log = logging.getLogger("red.raidensakura.genshinutils")


class GenshinNotes(commands.Cog):
    """GenshinUtils diary command class."""

    # https://discord.com/channels/133049272517001216/160386989819035648/1067445744497348639
    # This will get replaced by genshinutils.py's `genshin`
    # Thanks Jojo#7791!
    @commands.group()
    async def genshin(self, ctx: commands.Context):
        """GenshinUtils main command."""

    @genshin.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(2, 10, commands.BucketType.member)
    async def notes(self, ctx: commands.Context):
        """
        Display a Genshin Impact notes such as Resin amount, expedition status etc.
        Command require cookie registration.
        """

        async def generate_diary(uid):
            try:
                client = genshin.Client(cookie)
                data = await client.get_notes(uid)
            except Exception as exc:
                return await ctx.send(
                    f"Unable to retrieve data from Hoyolab API:\n`{exc}`"
                )
            e = generate_embed(
                f"Game Notes for {ctx.author.display_name}", await ctx.embed_color()
            )
            e.add_field(
                name="🌙 Resin",
                value=(
                    f"**{data.current_resin} / {data.max_resin}**\n\n"
                    f"Time until full\n[**{data.remaining_resin_recovery_time}**]"
                ),
                inline=True,
            )
            e.add_field(
                name="🪙 Realm Currency",
                value=(
                    f"**{data.current_realm_currency} / {data.max_realm_currency}**\n\n"
                    f"Time until full\n[**{data.remaining_realm_currency_recovery_time}**]"
                ),
                inline=True,
            )
            e.add_field(
                name="🎟️ Weekly Resin Discounts",
                value=f"**{data.remaining_resin_discounts} / {data.max_resin_discounts}**",
            )
            if data.claimed_commission_reward:
                bonus = "Bonus claimed."
            else:
                bonus = "Bonus unclaimed."
            e.add_field(
                name="📋 Daily Commission Status",
                value=(
                    f"**{data.completed_commissions} / {data.max_commissions}** completed\n\n"
                    f"{bonus}"
                ),
            )
            unix_date = data.transformer_recovery_time.timetuple()
            e.add_field(
                name="🛠️ Parametric Transformer",
                value=f"Recovery: \n<t:{int(mktime(unix_date))}:R>",
            )
            if data.expeditions:
                e.add_field(
                    name="🚩 Expedition Status",
                    value=f"You can deploy a maximum of **{data.max_expeditions} characters**.",
                    inline=False,
                )
                for expedition in data.expeditions:
                    e.add_field(
                        name=f"{expedition.character.name} ({expedition.status})  ",
                        value=f"Time left: **{expedition.remaining_time}**",
                    )

            return await ctx.send(embed=e)

        async def test_honkai():
            try:
                client = genshin.Client(cookie)
                data = await client.get_full_honkai_user(20177789)
            except Exception as exc:
                return await ctx.send(
                    f"Unable to retrieve data from Hoyolab API:\n`{exc}`"
                )
            return await log.debug(f"```{data}```")

        uid = await validate_uid(ctx.author, self.config)
        if not uid:
            return await ctx.send("You do not have a UID linked.")

        cookie = await get_user_cookie(self.config, ctx.author)
        if not cookie:
            return await ctx.send("No cookie.")

        with ctx.typing():
            # return await test_honkai()
            return await generate_diary(uid)
