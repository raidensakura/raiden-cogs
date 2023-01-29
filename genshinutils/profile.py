import io
import logging
import time
from typing import Union

import genshin

import discord
from redbot.core import checks, commands
from .constants import character_namecards
from .utils import generate_embed

from .utils import (
    enka_get_character_card,
    validate_char_name,
    validate_uid,
    get_user_cookie,
)

log = logging.getLogger("red.raidensakura.genshinutils")


class GenshinProfile(commands.Cog):
    """GenshinUtils profile command class."""

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
    async def profile(
        self,
        ctx: commands.Context,
        user_or_uid: Union[discord.Member, str, None],
        *,
        character: Union[str, None],
    ):
        """
        Display a Genshin Impact profile for a UID, Discord user or yourself.
        If a character name is provided, it will display character infographic instead.
        """

        async def enka_generate_profile(uid):
            try:
                data = await self.enka_client.fetch_user(uid)
            except Exception as exc:
                return await ctx.send(
                    f"Unable to retrieve data from enka.network:\n`{exc}`"
                )

            e = generate_embed(f"Profile for {data.player.nickname} [AR {data.player.level}]", await ctx.embed_color())
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
                value=f"{data.player.abyss_floor}-{data.player.abyss_room}",
            )

            return await ctx.send(embed=e)

        async def enka_generate_char_img(uid, char_name):
            with io.BytesIO() as image_binary:
                char_card = await enka_get_character_card(uid, char_name)
                if not char_card:
                    return await ctx.send(
                        "This user does not have that character featured."
                    )
                temp_filename = str(time.time()).split(".")[0] + ".png"
                log.debug(
                    f"[generate_char_info] Pillow object for character card:\n{char_card}"
                )
                first_card = next(iter(char_card.values()))
                card_object = next(iter(first_card.values()))
                card_object.save(image_binary, "PNG", optimize=True, quality=95)
                image_binary.seek(0)
                return await ctx.send(
                    file=discord.File(fp=image_binary, filename=temp_filename)
                )

        async def genshin_generate_profile(uid):
            try:
                client = genshin.Client(cookie)
                data = await client.get_partial_genshin_user(uid)
            except Exception as exc:
                return await ctx.send(
                    f"Unable to retrieve data from Hoyolab API:\n`{exc}`"
                )

            e = generate_embed(f"Profile for {data.info.nickname} [AR {data.info.level}]", await ctx.embed_color())
            if data.characters:
                e.set_thumbnail(url=data.characters[0].icon)
                if character_namecards[data.characters[0].name.title()]:
                    namecard_url = character_namecards[data.characters[0].name.title()]
                    e.set_image(url=namecard_url)
            e.add_field(name="Achievements", value=data.stats.achievements, inline=True)
            e.add_field(name="Days Active", value=data.stats.days_active, inline=True)
            e.add_field(
                name="Characters Unlocked", value=data.stats.characters, inline=True
            )
            e.add_field(
                name="Current Spiral Abyss Floor",
                value=data.stats.spiral_abyss,
                inline=True,
            )
            e.add_field(
                name="Total Oculi Collected",
                value=(
                    f"{data.stats.anemoculi + data.stats.geoculi + data.stats.electroculi + data.stats.dendroculi}"
                ),
                inline=True,
            )
            e.add_field(
                name="Waypoints Unlocked",
                value=(f"{data.stats.unlocked_waypoints}"),
                inline=True,
            )
            e.add_field(
                name="Total Chests Opened",
                value=(
                    f"{data.stats.common_chests + data.stats.precious_chests + data.stats.exquisite_chests + data.stats.luxurious_chests + data.stats.remarkable_chests}"
                ),
                inline=True,
            )
            e.add_field(
                name="Domains Unlocked",
                value=(f"{data.stats.unlocked_domains}"),
                inline=True,
            )

            return await ctx.send(embed=e)

        log.debug(f"[Args] user_or_uid: {user_or_uid}")
        log.debug(f"[Args] character: {character}")

        """If nothing is passed at all, we assume user is trying to generate their own profile"""
        if not user_or_uid and not character:
            uid = await validate_uid(ctx.author, self.config)
            if not uid:
                return await ctx.send("You do not have a UID linked.")

            cookie = await get_user_cookie(self.config, ctx.author)

            with ctx.typing():
                if not cookie:
                    return await enka_generate_profile(uid)

                return await genshin_generate_profile(uid)

        """
        Since both args are optional: [user_or_uid] [character]
        [character] could be passed as [user_or_uid]
        We check and handle it appropriately
        """
        if user_or_uid and not character:
            uid = await validate_uid(user_or_uid, self.config)
            if uid:
                with ctx.typing():
                    return await enka_generate_profile(uid)

            log.debug(
                f"[{ctx.command.name}] Not a UID, assuming it's a character name..."
            )
            char = validate_char_name(user_or_uid)
            if not char:
                return await ctx.send(
                    "Not a valid UID or character name that's not in dictionary."
                )

            log.debug(
                f"[{ctx.command.name}] Valid character name found, trying to fetch author UID..."
            )
            uid = await validate_uid(ctx.author, self.config)
            if not uid:
                return await ctx.send("You do not have a UID linked.")

            with ctx.typing():
                return await enka_generate_char_img(uid, char)

        """This handles if both [user_or_uid] and [character] are appropriately passed"""
        if user_or_uid and character:
            uid = await validate_uid(user_or_uid, self.config)
            if not uid:
                return await ctx.send(
                    "Not a valid UID or user does not have a UID linked."
                )

            char = validate_char_name(character)
            if not char:
                return await ctx.send("Character name invalid or not in dictionary.")

            with ctx.typing():
                return await enka_generate_char_img(uid, char)
