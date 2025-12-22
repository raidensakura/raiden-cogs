from redbot.core import commands

from .vars import GAME_NAMES

import logging

import genshin
import re
from discord import ui, TextStyle, ButtonStyle, Interaction, SelectOption

log = logging.getLogger("red.raidensakura.hoyotools")


class CookieManageView(ui.View):
    """A view to select, test, and remove saved cookies."""

    def __init__(
        self,
        cog,
        ctx: commands.Context,
        cookies: list[str],
        timeout: int = 180,
    ):
        super().__init__(timeout=timeout)
        # local imports to avoid touching top-of-file imports

        self.cog = cog
        self.ctx = ctx
        self.cookies = cookies
        self.selected_index: int | None = None

        # build options (simple preview / account_id_v2 detection)
        pattern = re.compile(r"account_id_v2=(\d+)")
        options: list["SelectOption"] = []
        for idx, cookie in enumerate(cookies, start=1):
            m = pattern.search(cookie)
            if m:
                desc = f"account_id_v2: {m.group(1)}"
            else:
                preview = cookie[:12] + "..." if len(cookie) > 15 else cookie
                desc = f"`{preview}`"
            options.append(
                SelectOption(
                    label=f"Cookie {idx}", description=desc[:100], value=str(idx - 1)
                )
            )

        if not options:
            options.append(
                SelectOption(
                    label="No cookies",
                    description="You have no saved cookies",
                    value="-1",
                    default=True,
                )
            )

        self.select = ui.Select(
            placeholder="Select a cookie...",
            options=options,
            min_values=1,
            max_values=1,
        )
        self.select.callback = self._on_select
        self.add_item(self.select)

        self.remove_btn = ui.Button(
            label="Remove", style=ButtonStyle.danger, disabled=True
        )
        self.remove_btn.callback = self._on_remove
        self.add_item(self.remove_btn)

        self.test_btn = ui.Button(
            label="Test Claim", style=ButtonStyle.primary, disabled=True
        )
        self.test_btn.callback = self._on_test
        self.add_item(self.test_btn)

        self.close_btn = ui.Button(label="Close", style=ButtonStyle.secondary)
        self.close_btn.callback = self._on_close
        self.add_item(self.close_btn)

    async def _verify_user(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "This menu isn't for you.", ephemeral=True
            )
            return False
        return True

    async def _on_select(self, interaction: Interaction):
        if not await self._verify_user(interaction):
            return
        val = self.select.values[0]
        try:
            idx = int(val)
        except Exception:
            await interaction.response.send_message(
                "Invalid selection.", ephemeral=True
            )
            return

        if idx < 0 or idx >= len(self.cookies):
            await interaction.response.send_message(
                "Invalid cookie selected.", ephemeral=True
            )
            return

        self.selected_index = idx
        # enable action buttons
        self.remove_btn.disabled = False
        self.test_btn.disabled = False

        await interaction.response.edit_message(
            content=f"Selected Cookie {idx+1}. Choose an action below.", view=self
        )

    async def _on_remove(self, interaction: Interaction):
        if not await self._verify_user(interaction):
            return
        if self.selected_index is None:
            await interaction.response.send_message(
                "No cookie selected.", ephemeral=True
            )
            return

        idx = self.selected_index
        cookies = list(await self.cog.config.user(self.ctx.author).cookies())
        if idx < 0 or idx >= len(cookies):
            await interaction.response.send_message(
                "Cookie not found (maybe removed already).", ephemeral=True
            )
            return

        # removed = cookies.pop(idx)
        await self.cog.config.user(self.ctx.author).cookies.set(cookies)
        # disable view after action
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"✅ Removed Cookie {idx+1}.", view=self
        )

    async def _on_test(self, interaction: Interaction):
        if not await self._verify_user(interaction):
            return
        if self.selected_index is None:
            await interaction.response.send_message(
                "No cookie selected.", ephemeral=True
            )
            return

        idx = self.selected_index
        cookie = self.cookies[idx]
        await interaction.response.defer(ephemeral=True)  # allow time for claim

        try:
            data = await self.cog.claim_daily(cookie)
        except Exception as e:
            await interaction.followup.send(f"❌ Test claim failed: {e}", ephemeral=True)
            return

        # build simple textual result
        lines = []
        if data.get("errors"):
            lines.append("Errors:\n" + "\n".join(data["errors"]))
        for game, msg in data.items():
            if game == "errors":
                continue
            lines.append(
                f"{self.cog.GAME_NAMES.get(game, game) if hasattr(self.cog, 'GAME_NAMES') else game}: {msg}"
            )

        resp = "\n".join(lines) if lines else "No results."
        # keep the view open, but inform user
        await interaction.followup.send(
            f"Test result for Cookie {idx+1}:\n{resp}", ephemeral=True
        )

    async def _on_close(self, interaction: Interaction):
        if not await self._verify_user(interaction):
            return
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content="Closed cookie manager.", view=self
        )

    async def on_timeout(self):
        try:
            # attempt to edit original message to disable components
            msg = None
            try:
                msg = await self.ctx.interaction.original_response()
            except Exception:
                pass
            for item in self.children:
                item.disabled = True
            if msg:
                await msg.edit(content="Cookie manager timed out.", view=self)
        except Exception:
            pass


class CookieModal(ui.Modal):
    title = "Add HoYoLAB Cookie"

    cookie = ui.TextInput(
        label="HoYoLAB Cookie",
        style=TextStyle.paragraph,
        placeholder="Paste your full cookie here",
        required=True,
        max_length=4000,
    )

    def __init__(self, cog, ctx: commands.Context):
        super().__init__()
        self.cog = cog
        self.ctx = ctx

    async def on_submit(self, interaction: Interaction):
        cookie = self.cookie.value.strip()
        user = interaction.user

        cookies = await self.cog.config.user(user).cookies()
        if cookie in cookies:
            await interaction.response.send_message(
                "❌ This cookie is already saved.",
                ephemeral=True,
            )
            return

        accounts = None
        try:
            self.cog.client.set_cookies(cookie)
            accounts = await self.cog.client.get_game_accounts()
        except genshin.InvalidCookies:
            await interaction.response.send_message(
                "❌ Invalid cookie.",
                ephemeral=True,
            )
            return
        except Exception:
            accounts = None

        cookies.append(cookie)
        await self.cog.config.user(user).cookies.set(cookies)

        if accounts:
            lines = []
            for a in accounts:
                uid = str(a.uid)
                censored = "xxx" + uid[3:] if len(uid) > 3 else uid
                lines.append(
                    f"- {GAME_NAMES.get(a.game_biz, a.game_biz)}: UID {censored}"
                )

            await interaction.response.send_message(
                "✅ Cookie added.\nAccounts:\n" + "\n".join(lines),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "✅ Cookie added.",
                ephemeral=True,
            )
