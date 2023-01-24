import logging, json

from redbot.core import checks, commands
from redbot.core.commands import Context

log = logging.getLogger("red.raidensakura.genshinutils")


class GenshinSet(commands.Cog):
    """
    Settings for GenshinUtils cog.
    """

    @commands.group()
    async def genshinset(self, ctx):
        """Settings for GenshinUtils cog."""

    @checks.is_owner()
    @genshinset.command()
    async def ltoken(self, ctx: commands.Context):
        """Instructions on how to set the `ltoken` secret."""
        await ctx.send(f"Use `{ctx.prefix}set api hoyolab ltoken your_ltoken_here`.")

    @checks.is_owner()
    @genshinset.command()
    async def ltuid(self, ctx: commands.Context):
        """Instructions on how to set the `ltuid` secret."""
        await ctx.send(f"Use `{ctx.prefix}set api hoyolab ltuid your_ltuid_here`.")

    @genshinset.command(name="uid", usage="<uid|remove|unlink>")
    @commands.guild_only()
    @commands.cooldown(2, 5, commands.BucketType.member)
    async def set_uid(self, ctx: commands.Context, uid_or_remove: str):
        """
        Link or unlink a Genshin Impact UID to your Discord account.
        For verification purpose, you will need to add your Discord tag to your in-game signature.
        It can take up to 15 minutes for your signature to be refreshed.
        """
        if uid_or_remove.lower() == "remove" or uid_or_remove.lower() == "unlink":
            await self.config.user(ctx.author).UID.clear()
            return await ctx.send(f"Successfully removed UID for {ctx.author.name}")
        else:
            uid = uid_or_remove
        if not len(uid) == 9 or not uid.isdigit():
            return await ctx.send("Not a valid UID.")

        try:
            reqmethod = self.session.get
            url = f"https://enka.network/u/{uid}/__data.json"
            async with reqmethod(url, headers={}, data={}) as req:
                data = await req.text()
                status = req.status
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError:
                    parsed = data
        except Exception as exc:
            log.error(exc)
            return await ctx.send("Error trying to fetch data from API [enka.network].")

        author_discord_id = f"{ctx.author.name}#{ctx.author.discriminator}"
        signature = parsed["playerInfo"]["signature"]
        if author_discord_id in signature:
            log.debug("UID and signature match")
            await self.config.user(ctx.author).UID.set(uid)
            return await ctx.send(f"Successfully set UID for {ctx.author.name} to {uid}")
        else:
            log.debug("UID and signature does not match")
            return await ctx.send(f"Your signature does not contain your Discord tag.\nNote that may take up to 15 minutes for changes to be reflected.")
