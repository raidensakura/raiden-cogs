import logging
import re
from operator import attrgetter
from re import escape

import genshin
from discord import Embed
from discord.channel import DMChannel
from redbot.core import commands

from .utils import decrypt_config, encrypt_config, generate_embed

log = logging.getLogger("red.raidensakura.genshinutils")


class GenshinRegister(commands.Cog):
    """GenshinUtils register command class."""

    # https://discord.com/channels/133049272517001216/160386989819035648/1067445744497348639
    # This will get replaced by genshinutils.py's `genshin`
    # Thanks Jojo#7791!
    @commands.group()
    async def genshin(self, ctx: commands.Context):
        """GenshinUtils main command."""

    @genshin.group()
    async def register(self, ctx: commands.Context):
        """Registration commands for GenshinUtils cog."""

    @register.command(name="uid", usage="<uid|remove>")
    @commands.cooldown(2, 5, commands.BucketType.member)
    async def set_uid(self, ctx: commands.Context, uid_or_remove: str):
        """
        Link or unlink a Genshin Impact UID to your Discord account.
        If verification is enabled, you need to add your Discord tag to your in-game signature.
        It can take up to 15 minutes for your signature to be refreshed.
        """

        async def verification_enabled():
            enabled = await self.config.verification()
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
            async with ctx.typing():
                data = await self.enka_client.fetch_user(uid)
        except Exception as exc:
            return await ctx.send(f"Unable to retrieve data from enka.network:\n`{exc}`")

        author_discord_id = f"{ctx.author.name}#{ctx.author.discriminator}"

        if await verification_enabled() and not pass_verification(
            author_discord_id, data.player.signature
        ):
            return await ctx.send(
                (
                    "Your signature does not contain your Discord tag.\n"
                    "It may take up to 15 minutes for changes to be reflected."
                )
            )
        await self.config.user(ctx.author).UID.set(uid)
        return await ctx.send(f"Successfully set UID for {ctx.author.name} to {uid}.")

    """
    Important Notes:
    1. This has proprietary DM check since to preface a disclaimer.
    2. I fully acknowledge storing the encryption key along 
       with the encrypted data itself is bad practice.
       Hoyolab account token can be used to performpotentially
       dangerous account actions. Since the cog is OSS, the purpose is 
       to prevent bot owners from having plaintext access to them
       in a way such that is require a bit of coding and encryption
       knowledge to access them on demand.
    """

    @register.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(2, 10, commands.BucketType.member)
    async def hoyolab(self, ctx: commands.Context, *, cookie: str = None):
        """Link or unlink a Hoyolab account token to your Discord account."""

        if not isinstance(ctx.channel, DMChannel):
            if cookie:
                try:
                    await ctx.message.delete()
                except Exception:
                    pass

            # Preface disclaimer
            app_info = await self.bot.application_info()
            if app_info.team:
                owner = app_info.team.name
            else:
                owner = app_info.owner
            desc = (
                "This command links your Hoyolab account token to your Discord account. "
                "This allow the bot to perform various account actions on your behalf, "
                "such as claiming daily login, fetching character data etc. "
                "Make sure you understand the risk of sharing your token online before proceeding."
                "\n\nPlease run this command in a DM channel when setting token."
                "\n\nRead on how to obtain your token [here](https://project-mei.xyz/genshinutils)."
            )
            e = generate_embed(
                title="Important Disclaimer", desc=desc, color=await ctx.embed_color()
            )
            if app_info.bot_public:
                public = "Can be invited by anyone."
            else:
                public = "Can only be invited by the owner."
            e.add_field(name="Bot Owner", value=owner)
            e.add_field(name="Bot Invite Link Privacy", value=public)
            if ctx.me.avatar_url:
                e.set_thumbnail(url=ctx.me.avatar_url)
            e.set_footer(text=f"Command invoked by {ctx.author}.")
            return await ctx.send(embed=e)

        if not cookie:
            cog_url = "https://project-mei.xyz/genshinutils"
            bot_prefix = f"{escape(ctx.prefix)}"
            command_name = f"{escape(ctx.command.name)}"
            msg = (
                f"**Provide a valid cookie to bind your Discord account to.**\n\n"
                f"` » ` Instruction on how to obtain your Hoyolab cookie:\n<{cog_url}>\n\n"
                f"` » ` For command help context: "
                f"`{bot_prefix}help genshin register {command_name}`\n\n"
                f"` » ` To read disclaimers, type this command again in any server."
            )
            return await ctx.send(msg)

        # Captures 2 groups: "ltuid=" and "abcd1234"
        re_uid = re.search(r"(ltuid=)([^;]*)", cookie)
        re_ltoken = re.search(r"(ltoken=)([^;]*)", cookie)

        if not re_uid:
            return await ctx.send("Not a valid `ltuid`.")
        if not re_ltoken:
            return await ctx.send("Not a valid `ltoken`.")

        ltuid = re_uid.group(2)
        ltoken = re_ltoken.group(2)

        # Verify if cookie is valid
        async with ctx.typing():
            try:
                cookies = {"ltuid": ltuid, "ltoken": ltoken}
                client = genshin.Client(cookies)
                accounts = await client.get_game_accounts()
            except Exception as exc:
                return await ctx.send(f"Unable to retrieve data from Hoyolab API:\n`{exc}`")
        """
        Accounts: [ GenshinAccount(lang="", game_biz="", level=int...), GenshinAccount(...) ]
        Recognized game_biz:
        bh3_global: Honkai Impact 3 Global
        hk4e_global: Genshin Impact
        """

        # Filter Genshin accounts only
        genshin_acc_list = []
        for account in accounts:
            if account.game_biz == "hk4e_global":
                genshin_acc_list.append(account)

        if not genshin_acc_list:
            return await ctx.send("Couldn't find a linked Genshin UID in your Hoyolab account.")

        # https://www.geeksforgeeks.org/python-get-the-object-with-the-max-attribute-value-in-a-list-of-objects/
        # get genshin account with the highest level
        highest_level_acc = max(genshin_acc_list, key=attrgetter("level"))
        uid = highest_level_acc.uid

        # Save cookie in config
        encoded_ltuid = await encrypt_config(self.config, ltuid)
        encoded_ltoken = await encrypt_config(self.config, ltoken)
        await self.config.user(ctx.author).UID.set(uid)
        await self.config.user(ctx.author).ltuid.set(encoded_ltuid)
        await self.config.user(ctx.author).ltoken.set(encoded_ltoken)

        # Debugging stuff
        log.debug(f"Encrypted credentials saved for {ctx.author}")

        decoded_ltuid = await decrypt_config(self.config, encoded_ltuid)

        log.debug(f"Decoded ltuid for {ctx.author}: {decoded_ltuid}")

        # Send success embed
        desc = (
            "Successfully bound Genshin account to your Discord account. " "Details are as follow."
        )
        e = Embed(
            color=(await ctx.embed_colour()),
            title="Account Binding Success",
            description=desc,
        )
        e.add_field(name="UID", value=highest_level_acc.uid)
        e.add_field(name="Nickname", value=highest_level_acc.nickname)
        e.add_field(name="Server", value=highest_level_acc.server_name)
        e.add_field(name="AR Level", value=highest_level_acc.level)
        e.add_field(name="Language", value=highest_level_acc.lang)
        e.set_thumbnail(url=ctx.message.author.avatar_url)

        return await ctx.send(embed=e)
