import logging

from redbot.core import checks, commands
from redbot.core.commands import Context

log = logging.getLogger("red.raidensakura.genshinutils")


class GenshinSet(commands.Cog):
    """GenshinUtils genshinset command class."""

    @commands.group()
    async def genshinset(self, ctx):
        """Various settings for GenshinUtils cog."""

    @checks.is_owner()
    @genshinset.command()
    async def ltoken(self, ctx: commands.Context):
        """(Unused) Instructions on how to set the `ltoken` secret."""
        await ctx.send(f"Use `{ctx.prefix}set api hoyolab ltoken your_ltoken_here`.")

    @checks.is_owner()
    @genshinset.command()
    async def ltuid(self, ctx: commands.Context):
        """(Unused) Instructions on how to set the `ltuid` secret."""
        await ctx.send(f"Use `{ctx.prefix}set api hoyolab ltuid your_ltuid_here`.")

    @checks.is_owner()
    @genshinset.command()
    async def verification(self, ctx: commands.Context, toggle: bool):
        """Globally enable or disable UID verification for GenshinUtils cog."""
        await self.config.verification.set(toggle)
        status = "enabled" if toggle else "disabled"
        return await ctx.send(f"Global UID verification has been {status}.")

    @genshinset.command(name="uid", usage="<uid|remove|unlink>")
    @commands.guild_only()
    @commands.cooldown(2, 5, commands.BucketType.member)
    async def set_uid(self, ctx: commands.Context, uid_or_remove: str):
        """
        Link or unlink a Genshin Impact UID to your Discord account.
        If verification is enabled, you need to add your Discord tag to your in-game signature.
        It can take up to 15 minutes for your signature to be refreshed.
        """

        async def verification_enabled():
            enabled = (
                await self.config.verification()
                # or await self.config.guild.verification()
            )
            return enabled

        def pass_verification(discordtag, signature):
            if discordtag == signature:
                return True

        if uid_or_remove.lower() == "remove" or uid_or_remove.lower() == "unlink":
            await self.config.user(ctx.author).UID.clear()
            return await ctx.send(f"Successfully removed UID for {ctx.author.name}.")

        uid = uid_or_remove

        if not len(uid) == 9 or not uid.isdigit():
            return await ctx.send("Invalid UID provided, it must consist of 9 digits.")

        try:
            with ctx.typing():
                data = await self.enka_client.fetch_user(uid)
        except Exception as exc:
            return await ctx.send(
                f"Unable to retrieve data from enka.network:\n`{exc}`"
            )

        author_discord_id = f"{ctx.author.name}#{ctx.author.discriminator}"

        if await verification_enabled() and not pass_verification(
            author_discord_id, data.player.signature
        ):
            return await ctx.send(
                f"Your signature does not contain your Discord tag.\nNote that it may take up to 15 minutes for changes to be reflected."
            )
        await self.config.user(ctx.author).UID.set(uid)
        return await ctx.send(f"Successfully set UID for {ctx.author.name} to {uid}.")
