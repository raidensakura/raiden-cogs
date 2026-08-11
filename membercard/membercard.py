import functools
import io
import logging

import discord

from redbot.core import Config, commands

from .card import DEFAULT_THEME, THEMES, render_card

log = logging.getLogger("red.raidensakura.membercard")

THEME_DESCRIPTIONS = {
    "classic": "An ID-badge style card with a barcode footer.",
    "laevatain": "A full-art profile card with a stat panel.",
    "fangyi": "A green-trimmed full-art profile card.",
    "yvonne": "A pink-trimmed full-art profile card.",
    "perlica": "A steel-blue full-art profile card.",
}


class ThemePicker(discord.ui.Select):
    """A private theme selector that refreshes the card preview when changed."""

    def __init__(self, cog: "MemberCard", member: discord.Member, theme: str):
        options = [
            discord.SelectOption(
                label=name.title(),
                value=name,
                description=THEME_DESCRIPTIONS.get(name),
                default=name == theme,
            )
            for name in THEMES
        ]
        super().__init__(
            placeholder="Choose a card theme",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="membercard_theme_picker",
        )
        self.cog = cog
        self.member = member

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message(
                "This theme picker isn't for you.", ephemeral=True
            )
            return

        theme = self.values[0]
        await interaction.response.defer()
        try:
            buffer = await self.cog._generate_card(self.member, theme_override=theme)
        except Exception as exc:
            log.exception(
                "Failed to generate theme preview for %s.", self.member.id, exc_info=exc
            )
            await interaction.edit_original_response(
                content="Something went wrong while generating that theme preview."
            )
            return

        await self.cog.config.user(self.member).theme.set(theme)
        self.view.set_theme(theme)
        embed = self.cog._theme_preview_embed(self.member, theme)
        file = discord.File(buffer, filename="membercard.png")
        await interaction.edit_original_response(
            content=None, embed=embed, attachments=[file], view=self.view
        )


class ThemePickerView(discord.ui.View):
    def __init__(self, cog: "MemberCard", member: discord.Member, theme: str):
        super().__init__(timeout=180)
        self.add_item(ThemePicker(cog, member, theme))

    def set_theme(self, theme: str) -> None:
        picker = self.children[0]
        for option in picker.options:
            option.default = option.value == theme


class MemberCard(commands.Cog):
    """
    Generates a welcome image for new members, complete with their avatar,
    username, join date, and roles. Supports multiple card themes.
    """

    __author__ = ["raidensakura"]
    __version__ = "1.1.0"

    default_guild = {"enabled": False, "channel": None}
    default_user = {"theme": None}

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=892034756, force_registration=True
        )
        self.config.register_guild(**self.default_guild)
        self.config.register_user(**self.default_user)

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """
        Thanks Sinbad!
        """
        pre_processed = super().format_help_for_context(ctx)
        s = "s" if len(self.__author__) > 1 else ""
        return f"{pre_processed}\n\nAuthor{s}: {', '.join(self.__author__)}\nCog Version: {self.__version__}"

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        """Clears the user's stored card theme preference, if any."""
        await self.config.user_from_id(user_id).clear()

    @staticmethod
    def _permission_tier(member: discord.Member) -> str:
        """Derives a tier from the member's actual guild permissions, rather than an
        arbitrary role-hierarchy position that may not reflect real authority."""
        if member.id == member.guild.owner_id:
            return "Owner"
        perms = member.guild_permissions
        if perms.administrator:
            return "Admin"
        if any(
            (
                perms.manage_guild,
                perms.manage_roles,
                perms.manage_channels,
                perms.kick_members,
                perms.ban_members,
                perms.manage_messages,
                perms.moderate_members,
            )
        ):
            return "Moderator"
        return "Member"

    async def _resolve_theme(self, member: discord.Member) -> str:
        """Returns the member's chosen theme if they've set a valid one, otherwise
        the default theme."""
        stored = await self.config.user(member).theme()
        return stored if stored in THEMES else DEFAULT_THEME

    async def _generate_card(
        self, member: discord.Member, *, theme_override: str = None
    ) -> io.BytesIO:
        # Interaction payloads can contain a lightweight Member without presence
        # activities. Prefer Red's cached guild member so theme-picker previews
        # receive the same custom-status data as prefix-command card renders.
        cached_member = member.guild.get_member(member.id)
        if cached_member is not None:
            member = cached_member

        avatar_bytes = await member.display_avatar.with_size(512).read()

        guild_icon_bytes = None
        if member.guild.icon:
            guild_icon_bytes = await member.guild.icon.with_size(256).read()

        roles = [
            (role.name, role.color.to_rgb())
            for role in reversed(member.roles)
            if not role.is_default()
        ]

        accent = member.color.to_rgb() if member.color.value else None
        theme = theme_override or await self._resolve_theme(member)
        if theme not in THEMES:
            theme = DEFAULT_THEME

        status_text = None
        for activity in member.activities:
            if isinstance(activity, discord.CustomActivity):
                status_text = activity.name
                break

        func = functools.partial(
            render_card,
            theme=theme,
            display_name=member.display_name,
            username=member.name,
            avatar_bytes=avatar_bytes,
            guild_name=member.guild.name,
            guild_icon_bytes=guild_icon_bytes,
            joined_at=member.joined_at,
            roles=roles,
            user_id=member.id,
            accent=accent,
            created_at=member.created_at,
            permission_tier=self._permission_tier(member),
            is_boosting=member.premium_since is not None,
            status_text=status_text,
        )
        return await self.bot.loop.run_in_executor(None, func)

    async def _build_welcome_embed(
        self, member: discord.Member
    ) -> tuple[discord.Embed, discord.File]:
        """Generates a welcome card and wraps it in a welcome embed.

        Uses the member's chosen theme if they've set one, otherwise `classic`.
        """
        theme = await self._resolve_theme(member)
        buffer = await self._generate_card(member, theme_override=theme)

        prefixes = await self.bot.get_valid_prefixes(member.guild)
        prefix = prefixes[0] if prefixes else "!"

        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}!",
            description=(
                f"{member.mention} just joined the server.\n"
                "Choose and preview your card theme with "
                f"`{prefix}membercard theme` or `/membercard theme`."
            ),
            color=member.color if member.color.value else discord.Color.blurple(),
        )
        embed.set_image(url="attachment://membercard.png")
        file = discord.File(buffer, filename="membercard.png")
        return embed, file

    @staticmethod
    def _theme_preview_embed(member: discord.Member, theme: str) -> discord.Embed:
        embed = discord.Embed(
            title="Choose your member card theme",
            description=(
                f"Selected theme: **{theme.title()}**\n"
                f"{THEME_DESCRIPTIONS.get(theme, '')}\n\n"
                "Choose another option below to preview it. Your selection is saved "
                "automatically."
            ),
            color=member.color if member.color.value else discord.Color.blurple(),
        )
        embed.set_image(url="attachment://membercard.png")
        return embed

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        guild = member.guild
        settings = await self.config.guild(guild).all()
        if not settings["enabled"]:
            return

        channel = (
            guild.get_channel(settings["channel"])
            if settings["channel"]
            else guild.system_channel
        )
        if channel is None:
            return

        perms = channel.permissions_for(guild.me)
        if not (perms.send_messages and perms.attach_files and perms.embed_links):
            return

        try:
            embed, file = await self._build_welcome_embed(member)
        except Exception as exc:
            log.exception(
                "Failed to generate member card for %s.", member.id, exc_info=exc
            )
            return

        try:
            await channel.send(embed=embed, file=file)
        except discord.HTTPException as exc:
            log.exception("Failed to send member card in %s.", channel.id, exc_info=exc)

    @commands.hybrid_group(name="membercard", aliases=["mcard"])
    @commands.guild_only()
    async def membercard(self, ctx: commands.Context):
        """Manage and view member ID cards."""

    @membercard.command(name="view")
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.bot_has_permissions(attach_files=True)
    async def membercard_view(
        self, ctx: commands.Context, member: discord.Member = None
    ):
        """View your own or another member's ID card."""
        member = member or ctx.author
        async with ctx.typing():
            try:
                buffer = await self._generate_card(member)
            except Exception as exc:
                log.exception(
                    "Failed to generate member card for %s.", member.id, exc_info=exc
                )
                await ctx.send("Something went wrong while generating that card.")
                return
        await ctx.send(file=discord.File(buffer, filename="membercard.png"))

    @membercard.command(name="testwelcome")
    @commands.guild_only()
    @commands.is_owner()
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    async def membercard_testwelcome(
        self, ctx: commands.Context, member: discord.Member = None
    ):
        """Owner-only: preview the welcome message as it would appear on join."""
        member = member or ctx.author
        async with ctx.typing():
            try:
                embed, file = await self._build_welcome_embed(member)
            except Exception as exc:
                log.exception(
                    "Failed to generate test welcome message for %s.",
                    member.id,
                    exc_info=exc,
                )
                await ctx.send(
                    "Something went wrong while generating the test welcome message."
                )
                return
        await ctx.send(embed=embed, file=file)

    @membercard.command(name="theme")
    @commands.guild_only()
    @commands.bot_has_permissions(attach_files=True, embed_links=True)
    async def membercard_theme(self, ctx: commands.Context):
        """
        Choose your personal member card theme from an interactive preview.

        Used by both `[p]membercard view` and your welcome card. Defaults to
        `classic` until you set one.
        """
        theme = await self._resolve_theme(ctx.author)
        async with ctx.typing():
            try:
                buffer = await self._generate_card(ctx.author, theme_override=theme)
            except Exception as exc:
                log.exception(
                    "Failed to generate theme preview for %s.",
                    ctx.author.id,
                    exc_info=exc,
                )
                await ctx.send(
                    "Something went wrong while generating that theme preview."
                )
                return

        await ctx.send(
            embed=self._theme_preview_embed(ctx.author, theme),
            file=discord.File(buffer, filename="membercard.png"),
            view=ThemePickerView(self, ctx.author, theme),
        )

    @membercard.command(name="toggle")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def membercard_toggle(self, ctx: commands.Context):
        """Toggle whether a card is posted when a member joins."""
        enabled = await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(not enabled)
        state = "disabled" if enabled else "enabled"
        await ctx.send(f"Welcome cards are now {state} for this server.")

    @membercard.command(name="channel")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def membercard_channel(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """
        Set the channel where welcome cards are posted.

        Leave blank to reset to the server's system channel.
        """
        await self.config.guild(ctx.guild).channel.set(channel.id if channel else None)
        if channel:
            await ctx.send(f"Welcome cards will now be posted in {channel.mention}.")
        else:
            await ctx.send(
                "Welcome cards will now be posted in the server's system channel."
            )
