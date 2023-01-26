import io
import logging
import time
from typing import Union

import discord
from aioenkanetworkcard import encbanner
from redbot.core import commands
from redbot.core.commands import Context

from .constants import common_names

log = logging.getLogger("red.raidensakura.genshinutils")


class GenshinProfile(commands.Cog):
    """GenshinUtils profile command class."""

    # https://discord.com/channels/133049272517001216/160386989819035648/1067445744497348639
    # This will get replaced by genshinutils.py's `genshin`
    # Thanks Jojo#7791!
    @commands.group()
    @commands.guild_only()
    async def genshin(self, ctx: commands.Context):
        """GenshinUtils main command."""

    @genshin.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(2, 10, commands.BucketType.member)
    async def profile(
        self,
        ctx: Context,
        user_or_uid: Union[discord.Member, str, None],
        *,
        character: Union[str, None],
    ):
        """
        Display a Genshin Impact profile for a UID, Discord user or yourself.
        If a character name is provided, it will display character infographic instead.
        """

        async def get_profile(uid):
            try:
                data = await self.enka_client.fetch_user(uid)
            except Exception as exc:
                return await ctx.send(
                    f"Unable to retrieve data from enka.network:\n`{exc}`"
                )

            e = discord.Embed(
                color=(await ctx.embed_colour()),
                description=(
                    f"```fix\n"
                    f"✨ :: Profile for {data.player.nickname} [AR {data.player.level}]```\n"
                ),
            )
            if data.player.characters_preview:
                char_str = ""
                for character in data.player.characters_preview:
                    if character.name == data.player.characters_preview[0].name:
                        char_str += f"{character.name}"
                    else:
                        char_str += f", {character.name}"
                e.add_field(
                    name="Characters in Showcase",
                    value=(f"```fix\n" f"{char_str}" f"```"),
                    inline=False,
                )
            e.set_thumbnail(url=data.player.avatar.icon.url)
            e.set_image(url=data.player.namecard.banner.url)
            e.add_field(name="Signature", value=f"{data.player.signature}")
            e.add_field(name="World Level", value=f"{data.player.world_level}")
            e.add_field(name="Achievements", value=data.player.achievement)
            e.add_field(
                name="Current Spiral Abyss Floor",
                value=f"{data.player.abyss_floor} - {data.player.abyss_room}",
            )

            try:
                return await ctx.send(embed=e)
            except Exception as exc:
                log.exception(
                    f"[{get_profile.__name__}] Error trying to send embed.",
                    exc_info=exc,
                )
                return await ctx.send(
                    "Oops, I encountered an error while trying to send the embed."
                )

        async def get_character_card(uid, char_name):
            async with encbanner.ENC(
                lang="en", splashArt=True, characterName=char_name
            ) as encard:
                ENCpy = await encard.enc(uids=uid)
                return await encard.creat(ENCpy, 2)

        async def validate_uid(u):
            if isinstance(u, discord.Member):
                uid = await self.config.user(u).get_raw("UID")
                if uid:
                    exist = "exist"
                else:
                    exist = "does not exist"
                log.debug(f"[{validate_uid.__name__}] UID {exist} in config.")

            elif isinstance(u, str) and len(u) == 9 and u.isdigit():
                uid = u
                log.debug(f"[{validate_uid.__name__}] This is a valid UID.")

            else:
                uid = None
                log.debug(f"[{validate_uid.__name__}] This is not a valid UID.")

            return uid

        def validate_char_name(arg):
            formal_name = {i for i in common_names if arg in common_names[i]}
            if formal_name:
                return str(formal_name).strip("{'\"}")

        async def generate_char_info(uid, char_name):
            """Generate character info"""
            with io.BytesIO() as image_binary:
                char_card = await get_character_card(uid, char_name)
                if not char_card:
                    return await ctx.send(
                        "This user does not have that character featured."
                    )
                temp_filename = str(time.time()).split(".")[0] + ".png"
                log.debug(
                    f"[{generate_char_info.__name__}] Pillow object for character card:\n{char_card}"
                )
                char_card[uid][char_name].save(
                    image_binary, "PNG", optimize=True, quality=95
                )
                image_binary.seek(0)
                return await ctx.send(
                    file=discord.File(fp=image_binary, filename=temp_filename)
                )

        log.debug(f"[Args] user_or_uid: {user_or_uid}")
        log.debug(f"[Args] character: {character}")

        """If nothing is passed at all, we assume user is trying to generate their own profile"""
        if not user_or_uid and not character:
            uid = await validate_uid(ctx.author)
            if not uid:
                return await ctx.send("You do not have a UID linked.")

            with ctx.typing():
                return await get_profile(uid)

        """
        Since both args are optional: [user_or_uid] [character]
        [character] could be passed as [user_or_uid]
        We check and handle it appropriately
        """
        if user_or_uid and not character:
            uid = await validate_uid(user_or_uid)
            if uid:
                with ctx.typing():
                    return await get_profile(uid)

            log.debug(
                f"[{get_profile.__name__}] Not a UID, assuming it's a character name..."
            )
            char = validate_char_name(user_or_uid)
            if not char:
                return await ctx.send(
                    "Not a valid UID or character name that's not in dictionary."
                )

            log.debug(
                f"[{get_profile.__name__}] Valid character name found, trying to fetch author UID..."
            )
            uid = await validate_uid(ctx.author)
            if not uid:
                return await ctx.send("You do not have a UID linked.")

            with ctx.typing():
                return await generate_char_info(uid, char)

        """This handles if both [user_or_uid] and [character] are appropriately passed"""
        if user_or_uid and character:
            uid = await validate_uid(user_or_uid)
            if not uid:
                return await ctx.send(
                    "Not a valid UID or user does not have a UID linked."
                )

            char = validate_char_name(character)
            if not char:
                return await ctx.send("Character name invalid or not in dictionary.")

            with ctx.typing():
                await generate_char_info(uid, char)
