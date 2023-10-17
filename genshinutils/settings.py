import logging

from redbot.core import commands

log = logging.getLogger("red.raidensakura.genshinutils")


class GenshinSet(commands.Cog):
    """GenshinUtils genshinset command class."""

    @commands.group()
    async def genshinset(self, ctx: commands.Context):
        """Various global settings for GenshinUtils cog."""

    @commands.is_owner()
    @genshinset.command()
    async def ltoken(self, ctx: commands.Context):
        """Instructions on how to set global `ltoken` secret."""
        await ctx.send(f"Use `{ctx.prefix}set api hoyolab ltoken your_ltoken_here`.")

    @commands.is_owner()
    @genshinset.command()
    async def ltuid(self, ctx: commands.Context):
        """Instructions on how to set global `ltuid` secret."""
        await ctx.send(f"Use `{ctx.prefix}set api hoyolab ltuid your_ltuid_here`.")

    @commands.is_owner()
    @genshinset.command()
    async def verification(self, ctx: commands.Context, toggle: bool):
        """
        Globally enable or disable UID verification for GenshinUtils cog.
        Only applicable for account-linking via signature check.
        """
        await self.config.verification.set(toggle)
        status = "enabled" if toggle else "disabled"
        return await ctx.send(f"Global UID verification has been {status}.")
