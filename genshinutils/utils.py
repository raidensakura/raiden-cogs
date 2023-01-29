from __future__ import annotations

import logging

import discord
from aioenkanetworkcard import encbanner
from cryptography.fernet import Fernet

from .constants import common_names

log = logging.getLogger("red.raidensakura.genshinutils")

# Used internally
def bytes_to_string(bytes):
    str = bytes.decode()
    return str


# Used internally
def string_to_bytes(str):
    bytes = str.encode()
    return bytes


"""
Accepts: config
Returns: str(encryption_key) or None
"""
# https://stackoverflow.com/questions/44432945/generating-own-key-with-python-fernet
async def get_encryption_key(config):
    key = string_to_bytes(await config.encryption_key())
    if not key or key is None:
        key = Fernet.generate_key()
        await config.encryption_key.set(bytes_to_string(key))
    return key


"""
Accepts: config, str(encoded)
Returns: str(decoded)
"""
# decrypt config
async def decrypt_config(config, encoded):
    to_decode = string_to_bytes(encoded)
    cipher_suite = Fernet(await get_encryption_key(config))
    decoded_bytes = cipher_suite.decrypt(to_decode)
    decoded = bytes_to_string(decoded_bytes)
    return decoded


"""
Accepts: config, str(decoded)
Returns: str(encoded)
"""
# encrypt config
async def encrypt_config(config, decoded):
    to_encode = string_to_bytes(decoded)
    cipher_suite = Fernet(await get_encryption_key(config))
    encoded_bytes = cipher_suite.encrypt(to_encode)
    encoded = bytes_to_string(encoded_bytes)
    return encoded


"""
Accepts: ( str(uid) | discord.Member ), self.config
Returns: str(uid) or None
"""
# validate uid
async def validate_uid(u, config):
    if isinstance(u, discord.Member):
        uid = await config.user(u).UID()
        if uid:
            exist = "exist"
        else:
            exist = "does not exist"
        log.debug(f"[validate_uid] UID {exist} in config.")

    elif isinstance(u, str) and len(u) == 9 and u.isdigit():
        uid = u
        log.debug(f"[validate_uid] This is a valid UID.")

    else:
        uid = None
        log.debug(f"[validate_uid] This is not a valid UID.")

    return uid


"""
Accepts: str(name_query)
Returns: str(formal_name) or None
"""
# validate_char_name
def validate_char_name(arg):
    formal_name = {i for i in common_names if arg in common_names[i]}
    if formal_name:
        return str(formal_name).strip("{'\"}")


"""
Accepts: str(uid), formal_name
Returns: { UID: { Character: <Pillow Object> } }
"""
# enka_get_character_card
async def enka_get_character_card(uid, char_name):
    async with encbanner.ENC(
        lang="en", splashArt=True, characterName=char_name
    ) as encard:
        ENCpy = await encard.enc(uids=uid)
        return await encard.creat(ENCpy, 2)


"""
Accepts: config, discord.Member
Returns: <Cookie Object>
"""
# get_user_cookie
async def get_user_cookie(config, user):
    ltuid_config = await config.user(user).ltuid()
    ltoken_config = await config.user(user).ltoken()

    if ltuid_config and ltoken_config:
        ltuid = await decrypt_config(config, ltuid_config)
        ltoken = await decrypt_config(config, ltoken_config)
        cookie = {"ltuid": ltuid, "ltoken": ltoken}

    return cookie


"""
Accepts: str(title), str(author), color
Returns: discord.Embed
"""
# generate_embed
def generate_embed(title, color):
    cog_url = "https://project-mei.xyz/genshinutils"
    e = discord.Embed(title=title, color=color, url=cog_url)
    e.set_footer(text="genshinutils cog by raidensakura", icon_url="https://avatars.githubusercontent.com/u/120461773?s=64&v=4")
    return e
