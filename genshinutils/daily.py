import logging

import genshin
from redbot.core import commands

from .utils import generate_embed, get_user_cookie, validate_uid

log = logging.getLogger("red.raidensakura.genshinutils")


class GenshinDaily(commands.Cog):
    """GenshinUtils daily command class."""

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
    async def daily(self, ctx: commands.Context):
        """
        Redeem your daily login reward from Hoyolab for Genshin Impact.
        Command require cookie registration.
        """

        async def redeem_daily():
            try:
                client = genshin.Client(cookie)
                client.default_game = genshin.Game.GENSHIN
                signed_in, claimed_rewards = await client.get_reward_info()
                reward = await client.claim_daily_reward()
            except genshin.AlreadyClaimed:
                e = generate_embed(
                    title="Genshin Impact Daily Login",
                    desc="Daily reward already claimed.",
                    color=await ctx.embed_color(),
                )
                e.add_field(name="Total Login", value=f"{claimed_rewards} days")
            except Exception as exc:
                return await ctx.send(f"Unable to retrieve data from Hoyolab API:\n`{exc}`")
            else:
                signed_in = "✅"
                e = generate_embed(
                    title="Genshin Impact Daily Login",
                    desc="Daily reward successfully claimed.",
                    color=await ctx.embed_color(),
                )
                e.set_thumbnail(reward.icon)
                e.add_field(name="Reward", value=f"{reward.name} x{reward.amount}")
                e.add_field(name="Total Login", value=f"{signed_in} {claimed_rewards + 1} days")
            return await ctx.send(embed=e)

        uid = await validate_uid(ctx.author, self.config)
        if not uid:
            return await ctx.send("You do not have a UID linked.")

        cookie = await get_user_cookie(self.config, ctx.author)
        if not cookie:
            return await ctx.send("No cookie.")

        with ctx.typing():
            return await redeem_daily()
