from __future__ import annotations

import logging

import discord
from aioenkanetworkcard import encbanner
from cryptography.fernet import Fernet

from .constants import common_names

log = logging.getLogger("red.raidensakura.genshinutils")


# https://stackoverflow.com/questions/44432945/generating-own-key-with-python-fernet
async def get_encryption_key(config):
    """Fetch and convert encryption key from config

    :param object config: Red V3 Config object
    :return str: Plaintext encryption key
    """
    key = await config.encryption_key()
    if not key or key is None:
        key = Fernet.generate_key()
        await config.encryption_key.set(key.decode())
    else:
        key = key.encode()
    return key


async def decrypt_config(config, encoded):
    """Decrypt encrypted config data

    :param object config: Red V3 Config object
    :param str encoded: encoded data
    :return str: decoded data
    """
    to_decode = encoded.encode()
    cipher_suite = Fernet(await get_encryption_key(config))
    decoded_bytes = cipher_suite.decrypt(to_decode)
    decoded = decoded_bytes.decode()
    return decoded


async def encrypt_config(config, decoded):
    """Encrypt unencrypted data to store in config

    :param object config: Red V3 Config object
    :param str decoded: data to encrypt
    :return str: encoded data
    """
    to_encode = decoded.encode()
    cipher_suite = Fernet(await get_encryption_key(config))
    encoded_bytes = cipher_suite.encrypt(to_encode)
    encoded = encoded_bytes.decode()
    return encoded


async def validate_uid(u, config):
    """Return user UID from config or check if UID is valid

    :param discord.Member or str u: User or UID to check
    :param object config: Red V3 Config object
    :return str: UID of the user if exist or valid
    """
    if isinstance(u, discord.Member):
        uid = await config.user(u).UID()
        if uid:
            exist = "exist"
        else:
            exist = "does not exist"
        log.debug(f"[validate_uid] UID {exist} in config.")

    elif isinstance(u, str) and len(u) == 9 and u.isdigit():
        uid = u
        log.debug("[validate_uid] This is a valid UID.")

    else:
        uid = None
        log.debug("[validate_uid] This is not a valid UID.")

    return uid


def validate_char_name(arg):
    """Validate character name against constants

    :param str arg: name to check
    :return str: Formal name of the character if exist
    """
    formal_name = {i for i in common_names if arg in common_names[i]}
    if formal_name:
        return str(formal_name).strip("{'\"}")


async def enka_get_character_card(uid, char_name):
    """Generate one or more character build image objects in a dict

    :param str uid: UID of the player
    :param str char_name: formal name of the character
    :return dict: dict containing Pillow image object for the character
    """
    async with encbanner.ENC(lang="en", splashArt=True, characterName=char_name) as encard:
        ENCpy = await encard.enc(uids=uid)
        return await encard.creat(ENCpy, 2)


async def get_user_cookie(config, user):
    """Retrieve user cookie from config

    :param object config: Red V3 Config object
    :param discord.Member user: Discord user to check for
    :return cookie: Cookie object for the user
    """
    ltuid_config = await config.user(user).ltuid()
    ltoken_config = await config.user(user).ltoken()

    if ltuid_config and ltoken_config:
        ltuid = await decrypt_config(config, ltuid_config)
        ltoken = await decrypt_config(config, ltoken_config)
        cookie = {"ltuid": ltuid, "ltoken": ltoken}

    return cookie


def generate_embed(title="", desc="", color=""):
    """Generate standardized Discord Embed usable for the whole cog

    :param str title: Title of the embed, defaults to ""
    :param str desc: Description of the embed, defaults to ""
    :param str color: Color of the embed, defaults to ""
    :return discord.Embed: Discord Embed object
    """
    cog_url = "https://project-mei.xyz/genshinutils"
    e = discord.Embed(title=title, description=desc, color=color, url=cog_url)
    e.set_footer(
        text="genshinutils cog by raidensakura",
        icon_url="https://avatars.githubusercontent.com/u/120461773?s=64&v=4",
    )
    return e
