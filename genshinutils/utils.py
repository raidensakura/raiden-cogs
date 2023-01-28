from __future__ import annotations

import logging

import discord
from aioenkanetworkcard import encbanner
from cryptography.fernet import Fernet

from .constants import common_names

log = logging.getLogger("red.raidensakura.genshinutils")


def bytes_to_string(bytes):
    str = bytes.decode()
    return str


def string_to_bytes(str):
    bytes = str.encode()
    return bytes


# https://stackoverflow.com/questions/44432945/generating-own-key-with-python-fernet
async def get_encryption_key(config):
    key = string_to_bytes(await config.encryption_key())
    if not key or key is None:
        key = Fernet.generate_key()
        await config.encryption_key.set(bytes_to_string(key))
    return key


async def decrypt_config(config, encoded):
    to_decode = string_to_bytes(encoded)
    cipher_suite = Fernet(await get_encryption_key(config))
    decoded_bytes = cipher_suite.decrypt(to_decode)
    decoded = bytes_to_string(decoded_bytes)
    return decoded


async def encrypt_config(config, decoded):
    to_encode = string_to_bytes(decoded)
    cipher_suite = Fernet(await get_encryption_key(config))
    encoded_bytes = cipher_suite.encrypt(to_encode)
    encoded = bytes_to_string(encoded_bytes)
    return encoded


async def validate_uid(u, self):
    if isinstance(u, discord.Member):
        uid = await self.config.user(u).get_raw("UID")
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


def validate_char_name(arg):
    formal_name = {i for i in common_names if arg in common_names[i]}
    if formal_name:
        return str(formal_name).strip("{'\"}")


async def get_character_card(uid, char_name):
    async with encbanner.ENC(
        lang="en", splashArt=True, characterName=char_name
    ) as encard:
        ENCpy = await encard.enc(uids=uid)
        return await encard.creat(ENCpy, 2)
