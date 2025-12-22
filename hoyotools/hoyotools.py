from .vars import SUPPORTED_GAMES, GAME_NAMES, FAIL_ICONS, SUCCESS_ICONS
from typing import Literal, Optional, Union

from redbot.core import commands
from discord.ext import tasks
from redbot.core.bot import Red
from redbot.core.config import Config
from .views import CookieModal, CookieManageView

import asyncio
from datetime import datetime

import logging
import random

import genshin
from discord import Embed, User, TextChannel, Forbidden
from discord.utils import utcnow
import re

log = logging.getLogger("red.raidensakura.hoyotools")

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class HoyoTools(commands.Cog):
    """
    A companion cog for Hoyoverse games
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=243316261264556032,
            force_registration=True,
        )
        self.config.register_user(
            cookies=[],
            auto_login=False,
            login_notify=True,
            redeem_codes=[],
        )
        self.config.register_global(
            auto_login_channel=None,
            auto_login=False,
            login_time=None,
            last_run=None,
        )
        self._task_lock = asyncio.Lock()

    async def cog_load(self):
        await super().cog_load()
        self.daily_task.start()

    async def cog_unload(self):
        await super().cog_unload()
        self.daily_task.cancel()

    async def red_delete_data_for_user(
        self, *, requester: RequestType, user_id: int
    ) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)

    def _make_client(self, cookie: str):
        client = genshin.Client(lang="en-us")
        client.set_cookies(cookie)
        return client

    async def claim_daily(self, cookie: str):
        client = self._make_client(cookie)
        results = {}
        errors = []

        try:
            accounts = await client.get_game_accounts()
        except genshin.InvalidCookies:
            return {"errors": ["Invalid cookie"]}

        game_accounts = {a.game_biz: a for a in accounts}

        for game, account in game_accounts.items():
            if game not in SUPPORTED_GAMES:
                continue

            uid = str(account.uid)
            censored = "xxx" + uid[3:]

            for _ in range(3):
                try:
                    reward = await client.claim_daily_reward(game=SUPPORTED_GAMES[game])
                    results[game] = f"✔ {reward.amount}× {reward.name} (UID {censored})"
                    break

                except genshin.AlreadyClaimed:
                    results[game] = f"✔ Already claimed (UID {censored})"
                    break

                except Exception as e:
                    errors.append(f"{GAME_NAMES.get(game)}: {e}")
                    break

        if errors:
            results["errors"] = errors

        return results

    async def redeem_codes(
        self,
        client: genshin.Client,
        game_accounts: dict[str, genshin.Game],
        codes: list[str],
    ):
        results = []
        remaining = set(codes)

        for code in codes:
            redeemed = False
            for game, account in game_accounts.items():
                if game not in SUPPORTED_GAMES:
                    continue

                uid = str(account.uid)
                censored = "xxx" + uid[3:]

                try:
                    res = await client.redeem_code(
                        code=code,
                        game=SUPPORTED_GAMES[game],
                    )
                    results.append(
                        f"🎁 Code `{code}` redeemed for {GAME_NAMES.get(game)} (UID {censored}): {res.message}"
                    )
                    redeemed = True
                    break

                except Exception as e:
                    msg_lower = str(e).lower()
                    # Handle common known responses without relying on non-existent exception types
                    if "already" in msg_lower or "already redeemed" in msg_lower:
                        results.append(
                            f"❌ Code `{code}` already redeemed for {GAME_NAMES.get(game)} (UID {censored})"
                        )
                        redeemed = True
                        break
                    if "invalid" in msg_lower or "not found" in msg_lower:
                        # Try next game
                        continue
                    results.append(
                        f"❌ Code `{code}` redemption error for {GAME_NAMES.get(game)} (UID {censored}): {e}"
                    )
                    redeemed = True
                    break

            if redeemed:
                remaining.discard(code)

        return results, remaining

    async def send_embed(
        self, userOrChannel: Union[User, TextChannel, commands.Context, None], data
    ):
        embed = Embed(
            title="HoYoLAB Daily Login",
            color=0xE86D82 if data.get("errors") else 0xA385DE,
        )

        embed.set_thumbnail(
            url=random.choice(FAIL_ICONS if data.get("errors") else SUCCESS_ICONS)
        )

        if data.get("errors"):
            embed.add_field(
                name="Errors",
                value="\n".join(data["errors"]),
                inline=False,
            )

        for game, msg in data.items():
            if game != "errors":
                embed.add_field(
                    name=GAME_NAMES.get(game, game),
                    value=msg,
                    inline=False,
                )

        # Determine target: Context -> DM author, User -> DM, TextChannel -> channel send
        if userOrChannel is None:
            return

        try:
            if isinstance(userOrChannel, commands.Context):
                target = userOrChannel.author
                await target.send(embed=embed)
            elif isinstance(userOrChannel, User):
                await userOrChannel.send(embed=embed)
            elif isinstance(userOrChannel, TextChannel):
                try:
                    await userOrChannel.trigger_typing()
                except Exception:
                    pass
                await userOrChannel.send(embed=embed)
            else:
                # Fallback: try to send if object supports send()
                await userOrChannel.send(embed=embed)
        except Exception as e:
            log.exception("Failed to send embed: " + str(e))

    async def _send(self, ctx, content=None, *, embed=None, ephemeral=True):
        if ctx.interaction:
            return await ctx.interaction.response.send_message(
                content=content, embed=embed, ephemeral=ephemeral
            )
        else:
            return await ctx.send(content=content, embed=embed)

    def _build_summary_embed(self, stats: dict) -> Embed:
        embed = Embed(
            title="📊 HoYoLAB Daily Auto Login Summary",
            color=0xA385DE,
            timestamp=utcnow(),
        )

        embed.add_field(name="👤 Users processed", value=str(stats["users"]))
        embed.add_field(name="🍪 Cookies processed", value=str(stats["cookies"]))
        embed.add_field(name="✅ Successful claims", value=str(stats["success"]))
        embed.add_field(name="✔ Already claimed", value=str(stats["already"]))
        embed.add_field(name="❌ Errors", value=str(stats["errors"]))

        if stats["per_game"]:
            games = "\n".join(
                f"{GAME_NAMES.get(g, g)}: {c}" for g, c in stats["per_game"].items()
            )
            embed.add_field(name="🎮 Games", value=games, inline=False)

        embed.set_footer(text="Hoyotools by raidensakura")

        return embed

    # ──────────────── COMMANDS ────────────────

    @commands.hybrid_group(name="hoyo", aliases=["hoyolab", "hoyotools"])
    async def hoyo(self, ctx: commands.Context):
        """Hoyotools top level command group"""

    @hoyo.group(name="cookie", aliases=["cookies"])
    async def cookie(self, ctx: commands.Context):
        """Hoyotools cookie management commands"""

    @hoyo.group(name="config")
    async def config(self, ctx: commands.Context):
        """Hoyotools configuration management commands"""

    @cookie.command(name="add")
    async def add_cookie(self, ctx: commands.Context, *, cookie: str = ""):
        """Add a cookie using a secure modal (slash-only)."""

        if not ctx.interaction:
            # Try delete the invoking message
            if cookie:
                try:
                    await ctx.message.delete()
                except Exception:
                    pass

            # Send ephemeral message only to the user
            await self._send(ctx, "Please use slash command to add a cookie.")
            return

        await ctx.interaction.response.send_modal(CookieModal(self, ctx))

    @cookie.command(name="remove")
    async def remove_cookie(self, ctx: commands.Context, cookie: str):
        """Remove a saved cookie by a given index."""

        cookies = await self.config.user(ctx.author).cookies()

        try:
            idx = int(cookie)
            if idx < 1 or idx > len(cookies):
                await ctx.interaction.response.send_message(
                    "❌ Invalid cookie index.",
                    ephemeral=True,
                )
                return
        except ValueError:
            await ctx.interaction.response.send_message(
                "❌ Invalid selection.",
                ephemeral=True,
            )
            return

        # removed = cookies.pop(idx - 1)
        await self.config.user(ctx.author).cookies.set(cookies)

        await ctx.interaction.response.send_message(
            "✅ Cookie removed.",
            ephemeral=True,
        )

    @cookie.command(name="list", aliases=["show", "ls"])
    async def list_cookie(self, ctx: commands.Context):
        """List your saved cookies and try to detect account_id_v2 to differentiate them."""
        cookies = await self.config.user(ctx.author).cookies()
        if not cookies:
            await self._send(ctx, "No cookies saved.")
            return

        pattern = re.compile(r"account_id_v2=(\d+)")
        embed = Embed(title="Saved cookies", color=0xA385DE)
        found_error = False

        for idx, cookie in enumerate(cookies, start=1):
            try:
                client = self._make_client(cookie)
                accounts = await client.get_game_accounts()
                if accounts:
                    parts = []
                    for a in accounts:
                        uid = str(a.uid)
                        censored = "xxx" + uid[3:] if len(uid) > 3 else uid
                        parts.append(
                            f"{GAME_NAMES.get(a.game_biz, a.game_biz)}: UID {censored}"
                        )
                    value = "\n".join(parts)
                else:
                    m = pattern.search(cookie)
                    if m:
                        value = f"account_id_v2: `{m.group(1)}`"
                    else:
                        preview = cookie[:12] + "..." if len(cookie) > 15 else cookie
                        value = f"`{preview}`"
            except genshin.InvalidCookies:
                value = "❌ Invalid cookie"
                found_error = True
            except Exception:
                m = pattern.search(cookie)
                if m:
                    value = f"account_id_v2: `{m.group(1)}`"
                else:
                    preview = cookie[:12] + "..." if len(cookie) > 15 else cookie
                    value = f"`{preview}`"

            embed.add_field(name=f"Cookie {idx}", value=value, inline=False)

        if found_error:
            embed.color = await ctx.embed_color()

        await self._send(ctx, embed=embed)

    @cookie.command(name="manage")
    async def manage_cookie(self, ctx: commands.Context):
        """Manage your saved cookies via a dropdown interaction (slash-only)."""
        if not ctx.interaction:
            # Try delete the invoking message
            try:
                await ctx.message.delete()
            except Exception:
                pass
            await self._send(ctx, "Please use the slash command to manage cookies.")
            return

        cookies = await self.config.user(ctx.author).cookies()
        if not cookies:
            await ctx.interaction.response.send_message(
                "❌ No cookies saved.", ephemeral=True
            )
            return

        view = CookieManageView(self, ctx, cookies)
        try:
            await ctx.interaction.response.send_message(
                "Select a cookie to manage:",
                view=view,
                ephemeral=True,
            )
        except Exception:
            # Fallback if ephemeral/send fails
            try:
                await ctx.interaction.response.send_message(
                    "Select a cookie to manage:", view=view
                )
            except Exception as e:
                log.exception("Failed to send manage cookie view: " + str(e))
                await self._send(ctx, "❌ Failed to open cookie manager.")

    @hoyo.command(name="redeem", aliases=["redeemcode", "redeemcodes"])
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def redeem(self, ctx: commands.Context, *, codes: str = ""):
        """Redeem game codes. Separate codes by spaces or commas or leave empty to use saved codes."""

        # ───── Resolve codes ─────
        if not codes:
            saved = await self.config.user(ctx.author).redeem_codes()
            if not saved:
                await self._send(ctx, "❌ No codes provided and no saved codes found.")
                return
            codes_set = {c.upper() for c in saved}
        else:
            parsed = [
                c.strip().upper() for c in re.split(r"[,\s]+", codes) if c.strip()
            ]
            if not parsed:
                await self._send(ctx, "❌ No valid codes provided.")
                return
            codes_set = set(parsed)

        # ───── Fetch cookies ─────
        cookies = await self.config.user(ctx.author).cookies()
        if not cookies:
            await self._send(ctx, "❌ No cookies saved.")
            return

        results: list[str] = []
        remaining_global = set(codes_set)

        # ───── Helper per-cookie task ─────
        async def redeem_for_cookie(idx: int, cookie: str, codes: set[str]):
            try:
                client = self._make_client(cookie)
                accounts = await client.get_game_accounts()
                game_accounts = {a.game_biz: a for a in accounts}

                res, remaining = await self.redeem_codes(
                    client,
                    game_accounts,
                    list(codes),
                )

                success = sum("🎁" in r for r in res)
                fail = sum("❌" in r for r in res)

                if res:
                    msg = (
                        f"Cookie {idx}: ✅ {success} success, ❌ {fail} failed\n"
                        + "\n".join(res)
                    )
                else:
                    msg = f"Cookie {idx}: No codes redeemed."

                return msg, set(remaining)

            except genshin.InvalidCookies:
                return f"Cookie {idx}: ❌ Invalid cookie", set(codes)

            except Exception as e:
                return f"Cookie {idx}: ❌ Redemption error: {e}", set(codes)

        # ───── Run concurrently ─────
        tasks = [
            redeem_for_cookie(idx, cookie, remaining_global)
            for idx, cookie in enumerate(cookies, start=1)
        ]

        async with ctx.typing():
            for coro in asyncio.as_completed(tasks):
                msg, remaining = await coro
                results.append(msg)
                remaining_global &= remaining
                if not remaining_global:
                    break

        # ───── Save remaining codes only if changed ─────
        try:
            saved = set(await self.config.user(ctx.author).redeem_codes())
            if saved != remaining_global:
                await self.config.user(ctx.author).redeem_codes.set(
                    list(remaining_global)
                )
        except Exception:
            log.exception("Failed to update saved redeem codes for user.")

        # ───── Build output ─────
        message = "\n\n".join(results) if results else "No redemption results."

        if remaining_global:
            message += "\n\n📌 Remaining codes saved to your config."

        # ───── Send safely ─────
        if len(message) > 1900:
            embed = Embed(
                title="HoYoLAB Code Redemption Results",
                description=message[:4000],
                color=0xA385DE,
            )
            await self._send(ctx, embed=embed)
        else:
            await self._send(ctx, message)

    # ──────────────── USER SETTINGS ────────────────

    @config.command(name="enablelogin")
    async def enable_autologin(
        self, ctx: commands.Context, enabled: Optional[bool] = None
    ):
        """Enable or disable auto login for your saved cookies. If no value is provided, toggles current state."""
        current = await self.config.user(ctx.author).auto_login()
        if enabled is None:
            enabled = not current

        if enabled:
            cookies = await self.config.user(ctx.author).cookies()
            if not cookies:
                await self._send(
                    ctx, "❌ No cookies saved. Add a cookie before enabling auto login."
                )
                return

        try:
            await self.config.user(ctx.author).auto_login.set(enabled)
        except Exception as e:
            await self._send(ctx, "❌ Failed to update auto login: " + str(e))
            return

        await self._send(
            ctx, ("✅ Auto login enabled." if enabled else "✅ Auto login disabled.")
        )

    @config.command(name="notifylogin")
    async def login_notify(self, ctx: commands.Context, enabled: Optional[bool] = None):
        """Enable or disable DM login notification. If no value is provided, toggles current state."""
        try:
            current = await self.config.user(ctx.author).login_notify()
        except Exception:
            current = False

        if enabled is None:
            enabled = not current

        try:
            await self.config.user(ctx.author).login_notify.set(enabled)
        except Exception as e:
            await self._send(ctx, "❌ Failed to update login notify: " + str(e))
            return

        await self._send(
            ctx,
            (
                "✅ Login notifications enabled."
                if enabled
                else "✅ Login notifications disabled."
            ),
        )

    # ──────────────── GLOBAL SETTINGS ────────────────

    @config.command(name="autologin")
    @commands.is_owner()
    async def set_global_autologin(
        self, ctx: commands.Context, enabled: Optional[bool] = None
    ):
        """Enable or disable global auto login. If no value is provided, toggles current state."""
        try:
            current = await self.config.auto_login()
        except Exception:
            current = False

        if enabled is None:
            enabled = not current

        try:
            await self.config.auto_login.set(enabled)
        except Exception as e:
            await self._send(ctx, "❌ Failed to update global auto login: " + str(e))
            return

        await self._send(
            ctx,
            (
                "✅ Global auto login enabled."
                if enabled
                else "✅ Global auto login disabled."
            ),
        )

    @config.command()
    @commands.is_owner()
    async def logchannel(self, ctx, channel_id: int):
        """Set the channel where the auto daily login messages are sent to. Set to 0 to disable."""
        if channel_id == 0:
            try:
                await self.config.auto_login_channel.set(None)
                await self._send(ctx, "Auto login disabled.")
            except Exception as e:
                await self._send(ctx, "Failed to disable auto login: " + str(e))
            return
        try:
            await self.config.auto_login_channel.set(channel_id)
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except Exception:
                    channel = None
            display = channel.mention if channel else f"<#{channel_id}>"
            await self._send(ctx, "Auto login logs channel set to " + display)
        except Exception as e:
            await self._send(ctx, "Failed to set channel ID: " + str(e))

    # ──────────────── USER COMMANDS ────────────────

    @hoyo.command()
    async def run(self, ctx):
        """Run daily login for account cookies saved in your user settings."""
        cookies = await self.config.user(ctx.author).cookies()
        if not cookies:
            await self._send(ctx, "No cookies saved.")
            return

        async with ctx.typing():
            for cookie in cookies:
                data = await self.claim_daily(cookie)
                await self.send_embed(ctx, data)

        await self._send(ctx, "✅ Daily login task completed.")

    # ──────────────── OWNER COMMANDS ────────────────

    @hoyo.command(name="status", aliases=["lastrun", "health"])
    @commands.is_owner()
    async def status(self, ctx):
        """Check the last run time of the daily auto-login task."""
        last = await self.config.last_run()
        if not last:
            await ctx.send("Last run: Never")
            return
        try:
            dt = datetime.fromisoformat(last)
            epoch = int((dt - datetime(1970, 1, 1)).total_seconds())
            await ctx.send(f"Last run: <t:{epoch}:F> (<t:{epoch}:R>)")
        except Exception:
            await ctx.send(f"Last run: {last}")

    @hoyo.command(name="runglobal")
    @commands.is_owner()
    async def runglobal(self, ctx: commands.Context):
        """Run the daily auto-login task manually for all users."""
        msg = await self._send(ctx, "🔄 Running global daily login task...")

        try:
            async with self._task_lock:
                await self._perform_auto_login()
        except Exception as e:
            log.exception("Failed to run global daily login task manually.")
            await msg.edit(content="❌ Global daily login task failed: " + str(e))
            return

        await self._send(ctx, "✅ Global daily login task completed.")

    # ──────────────── TASKS ────────────────

    @tasks.loop(minutes=1)
    async def daily_task(self):
        await self.bot.wait_until_ready()

        if not await self.config.auto_login():
            return

        login_time = await self.config.login_time() or "00:00"
        try:
            hour, minute = map(int, login_time.split(":"))
        except ValueError:
            log.error(f"Invalid login_time config: {login_time}")
            return

        now = utcnow()
        scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        last_run_str = await self.config.last_run()
        last_run = datetime.fromisoformat(last_run_str) if last_run_str else None

        # Missed run (bot offline / restart)
        if last_run is None or last_run.date() < now.date():
            if now >= scheduled:
                log.info("Performing missed auto login task.")
                async with self._task_lock:
                    await self._perform_auto_login()
                await self.config.last_run.set(utcnow().isoformat())
            return

        # Normal scheduled run
        if now >= scheduled and last_run < scheduled:
            log.info("Performing scheduled auto login task.")
            async with self._task_lock:
                await self._perform_auto_login()
            await self.config.last_run.set(utcnow().isoformat())

    async def _perform_auto_login(self):
        """Perform the auto login for all cookies and send embeds to channel and optionally DM users."""

        stats = {
            "users": 0,
            "cookies": 0,
            "success": 0,
            "already": 0,
            "errors": 0,
            "per_game": {},
        }

        channel_id = await self.config.auto_login_channel()
        channel: Optional[TextChannel] = None
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except Exception:
                    log.exception(
                        "Failed to fetch auto login channel, fallback to logging only."
                    )
                    channel = None

        try:
            users = await self.config.all_users()
        except Exception:
            log.exception("Failed to fetch user configs, auto login task aborted.")
            return

        for user_id, udata in users.items():
            try:
                if not udata.get("auto_login"):
                    continue

                cookies = udata.get("cookies", []) or []
                if not cookies:
                    continue

                user = self.bot.get_user(user_id)
                if not user:
                    continue

                for cookie in cookies:
                    data = await self.claim_daily(cookie)

                    # Send DM to user if they opted in
                    try:
                        if udata.get("login_notify", True) and user:
                            await self.send_embed(user, data)
                    except Forbidden:
                        pass

                    stats["cookies"] += 1
                    if "errors" in data:
                        stats["errors"] += 1
                    for game, msg in data.items():
                        if game == "errors":
                            continue
                        stats["per_game"].setdefault(game, 0)
                        stats["per_game"][game] += 1
                        if "Already claimed" in msg:
                            stats["already"] += 1
                        elif msg.startswith("✅"):
                            stats["success"] += 1

                stats["users"] += 1

            except Exception:
                log.exception(f"Failed processing auto login for user {user_id}")

        if channel:
            try:
                embed = self._build_summary_embed(stats)
                await channel.send(embed=embed)
            except Exception as e:
                log.exception("Failed to send auto login summary embed: " + str(e))

    @daily_task.before_loop
    async def before_daily(self):
        await self.bot.wait_until_ready()
