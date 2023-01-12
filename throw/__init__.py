from discord.utils import maybe_coroutine

from .throw import Throw

__red_end_user_data_statement__ = (
    "This cog does not persistently store any PII data or metadata about users."
)


async def setup(bot):
    await maybe_coroutine(bot.add_cog, Throw(bot))
