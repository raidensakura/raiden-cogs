from random import choice

import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import box, bold, quote
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from tabulate import tabulate

from .constants import *


class Throw(commands.Cog):
    """Throw stuff and your Discord friends or virtual strangers."""

    __authors__ = ["raidensakura"]
    __version__ = "1.2.0"

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Sinbad."""
        return (
            f"{super().format_help_for_context(ctx)}\n\n"
            f"Authors:  {', '.join(self.__authors__)}\n"
            f"Cog version:  v{self.__version__}"
        )

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        pass

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, 12345676985684321, force_registration=True)
        default_global = {"schema_version": 1}
        self.possible_actions = ["THROW"]
        default_user = {"ITEMS_THROWN": 0, "TIMES_HIT": 0}
        self.config.register_global(**default_global)
        self.config.register_member(**default_user)
        self.config.register_user(**default_user)

    @staticmethod
    async def temp_tip(ctx: commands.Context):
        pre = ctx.clean_prefix
        return await ctx.send(
            f"You can check your roleplay stats with `{pre}throwstats` command.",
            delete_after=10.0,
        )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 10, commands.BucketType.member)
    async def throw(self, ctx: Context, *, member: discord.Member):
        """Throw a random item at someone, with a GIF reaction"""
        if member.id == ctx.me.id:
            item = choice(ITEMS)
            message = (
                f"{ctx.author.mention} tried to throw {item[0]} to {ctx.me.mention},\n"
                "but unfortunately it was deflected, hitting them back."
            )
            em = discord.Embed(description=message, colour=await ctx.embed_colour())
            em.set_image(url="https://i.imgur.com/IX2IfuM.gif")
            return await ctx.send(embed=em)
        if member.id == ctx.author.id:
            return await ctx.send(
                f"Congratulations, **{ctx.author.name}**. " "You threw yourself."
            )
        async with ctx.typing():
            item = choice(ITEMS)
            hit = choice([True, False])
            items_thrown = await self.config.member(ctx.author).ITEMS_THROWN()
            times_hit = await self.config.member(member).TIMES_HIT()
            gitems_thrown = await self.config.user(ctx.author).ITEMS_THROWN()
            gtimes_hit = await self.config.user(member).TIMES_HIT()

            if hit:
                await self.config.member(ctx.author).ITEMS_THROWN.set(items_thrown + 1)
                await self.config.member(member).TIMES_HIT.set(times_hit + 1)
                await self.config.user(ctx.author).ITEMS_THROWN.set(gitems_thrown + 1)
                await self.config.user(member).TIMES_HIT.set(gtimes_hit + 1)
                message = (
                    f"_**{ctx.author.name}** threw {item[0]}_ at {member.mention}\n"
                    f"{choice(HIT)}"
                )
            else:
                message = (
                    f"_**{ctx.author.name}** threw {item[0]}_ at {member.mention}\n"
                    f"{choice(MISS)}"
                )

            embed = discord.Embed(description=message, colour=member.colour)

            if hit:
                embed.set_image(url=item[1])
                footer = (
                    f"{ctx.author.name} has thrown {items_thrown + 1} items so far.\n"
                    f"{member.name} has been hit {times_hit + 1} times so far!\n"
                )
                embed.set_footer(text=footer)

            return await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name="throwstats")
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(add_reactions=True, embed_links=True)
    async def throw_stats(self, ctx: Context, *, member: discord.Member = None):
        """Get your roleplay stats for this server."""
        user = member or ctx.author
        async with ctx.typing():
            actions_data = await self.config.member(user).all()
            global_actions_data = await self.config.user(user).all()
            colalign, header = (("left", "right", "right"), ["Action", "Hit", "Thrown"])
            people_with_no_creativity = []
            global_actions_array = []

            def parse_actions(data, array, action: str):
                for key, value in data.items():
                    if action in key:
                        sent = str(data.get(f"ITEMS_THROWN", " ")).replace("0", " ")
                        received = str(data.get(f"TIMES_HIT", " ")).replace("0", " ")
                        array.append([action.lower(), received, sent])

            for act in self.possible_actions:
                parse_actions(actions_data, people_with_no_creativity, act)

            def get_avatar(user):
                if discord.version_info.major >= 2:
                    return user.display_avatar.url
                return str(user.avatar_url)

            pages = []
            dedupe_list_1 = [
                x for i, x in enumerate(people_with_no_creativity, 1) if i % 2 != 0
            ]
            server_table = tabulate(
                dedupe_list_1, headers=header, colalign=colalign, tablefmt="psql"
            )
            emb = discord.Embed(
                colour=await ctx.embed_colour(), description=box(server_table, "nim")
            )
            emb.set_author(name=f"Throw Stats | {user.name}", icon_url=get_avatar(user))
            emb.set_footer(text="Go to next page to see your global throw stats!")
            pages.append(emb)

            for action in self.possible_actions:
                parse_actions(global_actions_data, global_actions_array, action)

            dedupe_list_2 = [
                x for i, x in enumerate(global_actions_array, 1) if i % 2 != 0
            ]
            global_table = tabulate(
                dedupe_list_2, headers=header, colalign=colalign, tablefmt="psql"
            )
            embed = discord.Embed(
                colour=await ctx.embed_colour(), description=box(global_table, "nim")
            )
            embed.set_author(
                name=f"Global Throw Stats | {user.name}", icon_url=get_avatar(user)
            )
            embed.set_footer(
                text=f"Requester: {ctx.author}", icon_url=get_avatar(ctx.author)
            )
            pages.append(embed)

        await menu(ctx, pages, DEFAULT_CONTROLS, timeout=60.0)
