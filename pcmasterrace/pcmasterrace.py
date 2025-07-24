import discord
from redbot.core import commands, Config
import json
import re
from .utils import (
    get_page,
    draw_bar_graph,
    build_combo_embed,
    DEFAULT_WEIGHT,
    DEFAULT_COLOR,
    CPU_SCORES_PATH,
    GPU_SCORES_PATH,
    WEIGHTS_PATH,
)
from .views import ScoreView, UserScoreView
from redbot.core.utils.views import SimpleMenu
import logging

with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
    WEIGHTS = json.load(f)

log = logging.getLogger("red.raidensakura.pcmasterrace")

class PCMasterRace(commands.Cog):
    """Submit and rank your CPU/GPU combos!"""

    default_user = {"cpu": None, "gpu": None}

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        self.config.register_user(**self.default_user)

        with open(CPU_SCORES_PATH, "r", encoding="utf-8") as f:
            self.cpu_scores = json.load(f)
        with open(GPU_SCORES_PATH, "r", encoding="utf-8") as f:
            self.gpu_scores = json.load(f)

    async def cog_load(self):
        await self.migrate_user_combos()

    async def migrate_user_combos(self):
        # Migrate user configs: convert saved CPU/GPU strings to full part names if needed
        all_users = await self.config.all_users()
        updated = False
        for user_id, data in all_users.items():
            cpu = data.get("cpu")
            gpu = data.get("gpu")
            new_cpu = None
            new_gpu = None
            if cpu:
                match = await self.regex_match(cpu, self.cpu_scores.keys())
                if match and match != cpu:
                    new_cpu = match
            if gpu:
                match = await self.regex_match(gpu, self.gpu_scores.keys())
                if match and match != gpu:
                    new_gpu = match
            if new_cpu or new_gpu:
                user_conf = self.config.user_from_id(user_id)
                if new_cpu:
                    await user_conf.cpu.set(new_cpu)
                if new_gpu:
                    await user_conf.gpu.set(new_gpu)
                updated = True
        if updated:
            log.info("Migrated user combos to full part names in config.")

    @commands.group(aliases=["pcmr"])
    @commands.guild_only()
    async def pcmasterrace(self, ctx):
        """PC Master Race commands."""
        pass

    async def regex_match(self, name, candidates, return_options=False, ctx=None):
        """
        Attempts to find the best matching candidate(s) from a list based on the provided name using several strategies:
        1. Case-insensitive exact match.
        2. Case-insensitive, normalized (alphanumeric, no spaces) match.
        3. Case-insensitive regex match for whole words or numbers (e.g., "3080" matches "RTX 3080", "i7-12700K" matches "Intel Core i7-12700K").
        4. Case-insensitive substring match (in either direction).
        If return_options is True and multiple matches are found, prompts the user to select one (requires ctx).
        Args:
            name (str): The name to match against the candidates.
            candidates (Iterable[str]): A collection of candidate strings to search.
            return_options (bool): If True, return all matches and prompt user if multiple.
            ctx: The command context (required if return_options is True and multiple matches).
        Returns:
            str or None: The best matching candidate string, or None if no match is found.
        """

        def normalize(s):
            return re.sub(r"[\W_]+", "", s).lower()

        name_norm = normalize(name)
        candidates = list(candidates)
        matches = []

        # 1. Case-insensitive exact match
        for key in candidates:
            if key.lower() == name.lower():
                matches.append(key)
        if matches:
            if return_options and len(matches) > 1 and ctx:
                return await self._prompt_user_choice(ctx, matches, name)
            return matches[0]

        # 2. Normalized (alphanumeric, no spaces) match
        for key in candidates:
            if normalize(key) == name_norm:
                matches.append(key)
        if matches:
            if return_options and len(matches) > 1 and ctx:
                return await self._prompt_user_choice(ctx, matches, name)
            return matches[0]

        # 3. Regex: match as a whole word or model code
        pattern = re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)
        for key in candidates:
            if pattern.search(key):
                matches.append(key)
        if matches:
            if return_options and len(matches) > 1 and ctx:
                return await self._prompt_user_choice(ctx, matches, name)
            return matches[0]

        # 4. Substring match (in either direction)
        for key in candidates:
            if name.lower() in key.lower() or key.lower() in name.lower():
                matches.append(key)
        if matches:
            if return_options and len(matches) > 1 and ctx:
                return await self._prompt_user_choice(ctx, matches, name)
            return matches[0]

        return None

    async def _prompt_user_choice(self, ctx, options, name):
        """
        Helper to prompt the user to select from multiple options.
        """
        if len(options) == 1:
            return options[0]
        desc = "\n".join(f"{i+1}. `{opt}`" for i, opt in enumerate(options))
        prompt = (
            f"Multiple matches found for `{name}`. Please reply with the number of your choice:\n{desc}"
        )
        await ctx.send(prompt)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit() and 1 <= int(m.content) <= len(options)

        try:
            msg = await ctx.bot.wait_for("message", check=check, timeout=30)
            idx = int(msg.content) - 1
            return options[idx]
        except Exception:
            await ctx.send("No valid selection made. Cancelling.")
            return None

    async def fetch_all_gpu_scores(self, gpu_name: str = ""):
        """
        Fetches and calculates weighted GPU scores for all GPUs or a specific GPU.
        If a GPU name is provided, attempts to match it using regex and returns the weighted scores
        for the matched GPU. If no match is found, returns an empty dictionary. If no GPU name is
        provided, returns weighted scores for all GPUs.
        Each GPU's scores are calculated using predefined weights, and the weighted total is included
        in the result.
        Args:
            gpu_name (str, optional): The name of the GPU to fetch scores for. Defaults to "".
        Returns:
            dict: A dictionary mapping GPU names to their score details, including the weighted score.
        """

        scores = {}
        items = self.gpu_scores.items()
        if gpu_name:
            match = await self.regex_match(gpu_name, self.gpu_scores.keys())
            if match:
                items = [(match, self.gpu_scores[match])]
            else:
                return {}
        for name, data in items:
            weighted = 0
            score_details = {}
            for score_name, value in data.items():
                weight = WEIGHTS.get(score_name, DEFAULT_WEIGHT)
                score_details[score_name] = value
                weighted += value * weight
            score_details["weighted"] = int(round(weighted))
            scores[name] = score_details
        return scores

    async def fetch_all_cpu_scores(self, cpu_name: str = ""):
        """
        Fetches and calculates weighted CPU scores for all CPUs or a specific CPU.
        If a CPU name is provided, attempts to match it against known CPU names using regex.
        Returns the weighted scores for the matched CPU if found, otherwise returns an empty dictionary.
        If no CPU name is provided, returns weighted scores for all CPUs.
        Args:
            cpu_name (str, optional): The name of the CPU to fetch scores for. Defaults to "".
        Returns:
            dict: A dictionary mapping CPU names to their score details, including individual scores and the weighted total.
        """

        scores = {}
        items = self.cpu_scores.items()
        if cpu_name:
            match = await self.regex_match(cpu_name, self.cpu_scores.keys())
            if match:
                items = [(match, self.cpu_scores[match])]
            else:
                return {}
        for name, data in items:
            weighted = 0
            score_details = {}
            for score_name, value in data.items():
                weight = WEIGHTS.get(score_name, DEFAULT_WEIGHT)
                score_details[score_name] = value
                weighted += value * weight
            score_details["weighted"] = int(round(weighted))
            scores[name] = score_details
        return scores

    async def fetch_gpu_score(self, gpu_name):
        """
        Calculates and returns the weighted score for a given GPU name.
        This method attempts to match the provided GPU name against known GPU scores.
        If a match is found, it computes a weighted sum of the GPU's scores using predefined weights.
        If no match is found, it returns 0.
        Args:
            gpu_name (str): The name of the GPU to fetch the score for.
        Returns:
            int: The weighted score for the GPU, or 0 if no match is found.
        """

        match = await self.regex_match(gpu_name, self.gpu_scores.keys())
        if match:
            gpu_data = self.gpu_scores[match]
            weighted = 0
            for score_name, value in gpu_data.items():
                weight = WEIGHTS.get(score_name, DEFAULT_WEIGHT)
                weighted += value * weight
            return int(round(weighted))
        return 0

    async def fetch_cpu_score(self, cpu_name):
        """
        Calculates and returns the weighted CPU score for a given CPU name.
        This method attempts to match the provided CPU name against known CPU scores.
        If a match is found, it computes a weighted sum of the CPU's scores using predefined weights.
        If no match is found, it returns 0.
        Args:
            cpu_name (str): The name of the CPU to fetch the score for.
        Returns:
            int: The weighted CPU score if a match is found, otherwise 0.
        """

        match = await self.regex_match(cpu_name, self.cpu_scores.keys())
        if match:
            cpu_data = self.cpu_scores[match]
            weighted = 0
            for score_name, value in cpu_data.items():
                weight = WEIGHTS.get(score_name, DEFAULT_WEIGHT)
                weighted += value * weight
            return int(round(weighted))
        return 0

    def combined_score(self, cpu_score, gpu_score, resolution="1440p"):
        """
        Calculates a combined performance score based on CPU and GPU scores,
        adjusted for the specified display resolution.
        The GPU score is scaled by a bias factor depending on the resolution:
            - "1080p": 0.7
            - "1440p": 0.8 (default)
            - "4k": 0.9
        The final score is the minimum of the CPU score and the biased GPU score,
        rounded to the nearest integer.
        Args:
            cpu_score (float or int): The performance score of the CPU.
            gpu_score (float or int): The performance score of the GPU.
            resolution (str, optional): The display resolution.
                Supported values are "1080p", "1440p", and "4k". Defaults to "1440p".
        Returns:
            int: The combined performance score.
        """

        bias = {"1080p": 0.7, "1440p": 0.8, "4k": 0.9}
        gpu_bias = bias.get(resolution, 0.8)
        return int(round(min(cpu_score, gpu_score * gpu_bias)))

    async def get_all_users(self, guild):
        """
        Asynchronously retrieves all users from the guild who have both CPU and GPU data configured.
        Args:
            guild (discord.Guild): The guild from which to retrieve members.
        Returns:
            list: A list of tuples, each containing a discord.Member object and their associated configuration data.
                  Only users with both 'cpu' and 'gpu' data are included.
        """

        users = []
        for user_id in await self.config.all_users():
            member = guild.get_member(user_id)
            if not member:
                continue
            data = await self.config.user_from_id(user_id).all()
            if data["cpu"] and data["gpu"]:
                users.append((member, data))
        return users

    @pcmasterrace.group(name="chart")
    async def chart(self, ctx):
        """Show leaderboard for all parts or server member's build."""
        pass

    @chart.command(name="parts")
    async def chart_parts(self, ctx):
        """List all GPU and CPU scores as a bar graph image with interactive buttons and pagination (embed only)."""
        if not self.gpu_scores and not self.cpu_scores:
            await ctx.send("No GPU or CPU scores set.")
            return

        # Prepare separate dicts for GPU and CPU weighted scores
        gpu_weighted_scores = {}
        cpu_weighted_scores = {}

        for name in self.gpu_scores.keys():
            gpu_weighted_scores[name] = await self.fetch_gpu_score(name)
        for name in self.cpu_scores.keys():
            cpu_weighted_scores[name] = await self.fetch_cpu_score(name)

        # Sort GPU and CPU scores by weighted score, highest first
        gpu_weighted_scores = dict(sorted(gpu_weighted_scores.items(), key=lambda x: x[1], reverse=True))
        cpu_weighted_scores = dict(sorted(cpu_weighted_scores.items(), key=lambda x: x[1], reverse=True))

        view = ScoreView(ctx, gpu_weighted_scores, cpu_weighted_scores)
        await self.send_view(ctx, view, cpu_weighted_scores)

    @chart.command(name="users")
    async def chart_users(self, ctx):
        """
        Show a bar graph comparing all server members' builds (CPU+GPU combos).
        """
        users = await self.get_all_users(ctx.guild)
        if not users:
            await ctx.send("No users have submitted combos.")
            return

        cpu_scores = {}
        gpu_scores = {}
        combined_scores = {}

        for member, data in users:
            cpu_score = await self.fetch_cpu_score(data["cpu"])
            gpu_score = await self.fetch_gpu_score(data["gpu"])
            combo_score = self.combined_score(cpu_score, gpu_score)
            cpu_scores[member.display_name] = cpu_score
            gpu_scores[member.display_name] = gpu_score
            combined_scores[member.display_name] = combo_score

        cpu_scores = dict(sorted(cpu_scores.items(), key=lambda x: x[1], reverse=True))
        gpu_scores = dict(sorted(gpu_scores.items(), key=lambda x: x[1], reverse=True))
        combined_scores = dict(sorted(combined_scores.items(), key=lambda x: x[1], reverse=True))

        view = UserScoreView(ctx, cpu_scores, gpu_scores, combined_scores)
        await self.send_view(ctx, view, cpu_scores)

    async def send_view(self, ctx, view, cpu_scores):
        """
        Sends an embed message displaying CPU scores with a bar graph image and interactive pagination buttons.
        Args:
            ctx: The context in which the command was invoked.
            view: The discord UI view containing pagination buttons.
            cpu_scores: A list of CPU score data to be displayed.
        Side Effects:
            - Sends a message to the Discord channel with an embed and optional image attachment.
            - Updates the state of pagination buttons based on the number of pages.
            - Stores the sent message in the view for future reference.
        """

        page_scores, total_pages = get_page(cpu_scores, 0)
        title = f"CPU Scores (Page 1/{total_pages})"
        img_bytes = draw_bar_graph(page_scores, title)
        embed = discord.Embed(title=title, color=await ctx.embed_color() or DEFAULT_COLOR)
        files = []
        view.prev_button.disabled = True
        view.next_button.disabled = total_pages <= 1
        if img_bytes:
            file = discord.File(img_bytes, filename="userscores.png")
            files = [file]
            embed.set_image(url="attachment://userscores.png")
        sent = await ctx.send(embed=embed, view=view, files=files)
        view.message = sent

    @pcmasterrace.group(name="set")
    async def set_cmd(self, ctx):
        """Set various settings for this cog."""
        pass

    @pcmasterrace.group(name="view")
    async def view_cmd(self, ctx):
        """View combos."""
        pass

    @set_cmd.command(name="combo")
    async def combo_set(self, ctx, *, combo: str = ""):
        """
        Set, update, or remove your CPU/GPU combo.
        Example usage: `pcmr set combo Ryzen 7 5800X + RTX 3080`\n

        If you already have a combo, it will be updated.
        To remove your combo, use: `pcmr set combo remove`
        """
        if combo is None:
            await ctx.send_help(ctx.command)
            return
        if combo.strip().lower() == "remove":
            await self.config.user(ctx.author).set(self.default_user)
            await ctx.send("Your combo has been removed.")
            return

        parts = re.split(r"\+|,|/", combo)
        if len(parts) < 2:
            await ctx.send(
                f"Please provide both CPU and GPU, e.g:\n`{ctx.prefix}pcmr set combo 5700X + RTX 3080`"
            )
            return

        cpu_name = parts[0].strip()
        gpu_name = parts[1].strip()

        matched_cpu = await self.regex_match(cpu_name, self.cpu_scores.keys(), return_options=True, ctx=ctx)
        matched_gpu = await self.regex_match(gpu_name, self.gpu_scores.keys(), return_options=True, ctx=ctx)

        if not matched_cpu:
            await ctx.send(f"Could not find CPU score for `{cpu_name}`.")
            return
        if not matched_gpu:
            await ctx.send(f"Could not find GPU score for `{gpu_name}`.")
            return

        cpu_scores = await self.fetch_all_cpu_scores(matched_cpu)
        gpu_scores = await self.fetch_all_gpu_scores(matched_gpu)

        await self.config.user(ctx.author).cpu.set(matched_cpu)
        await self.config.user(ctx.author).gpu.set(matched_gpu)

        embed = build_combo_embed(
            self,
            ctx.author,
            matched_cpu,
            matched_gpu,
            cpu_scores,
            gpu_scores,
            embed_color=await ctx.embed_color() or DEFAULT_COLOR,
            combined_score_title="Your combo has been set!",
        )
        await ctx.send(embed=embed)

    @view_cmd.command(name="combo")
    async def combo_view(self, ctx, member: discord.Member = None):
        """View your or another member's combo."""
        member = member or ctx.author
        data = await self.config.user(member).all()
        if not data["cpu"] or not data["gpu"]:
            await ctx.send(f"{member.display_name} has not submitted a combo.")
            return

        cpu_scores = await self.fetch_all_cpu_scores(data["cpu"])
        gpu_scores = await self.fetch_all_gpu_scores(data["gpu"])

        embed = build_combo_embed(
            self,
            member,
            data["cpu"],
            data["gpu"],
            cpu_scores,
            gpu_scores,
            embed_color=await ctx.embed_color() or DEFAULT_COLOR,
        )
        await ctx.send(embed=embed)

    @pcmasterrace.command(name="wiki")
    async def wiki(self, ctx):
        """
        Show information about how scores and combos work (multi-page).
        """
        # Page 1: Score calculation, types, weights, formula
        cpu_score_types = set()
        gpu_score_types = set()
        for cpu in self.cpu_scores.values():
            cpu_score_types.update(cpu.keys())
        for gpu in self.gpu_scores.values():
            gpu_score_types.update(gpu.keys())

        page1 = (
            "**How scores are calculated:**\n"
            "Each CPU and GPU has several benchmark scores. Each score is multiplied by a weight (defined in the config), "
            "then all weighted scores are summed to get a final weighted score for the part.\n\n"
            "**CPU Score Types & Weights:**\n"
        )
        for score_type in cpu_score_types:
            weight = WEIGHTS.get(score_type, DEFAULT_WEIGHT)
            page1 += f"- `{score_type}`: weight = `{weight}`\n"
        page1 += "\n**GPU Score Types & Weights:**\n"
        for score_type in gpu_score_types:
            weight = WEIGHTS.get(score_type, DEFAULT_WEIGHT)
            page1 += f"- `{score_type}`: weight = `{weight}`\n"
        page1 += (
            "\n**Combo Score Formula:**\n"
            "Your combo score is calculated as the minimum of your CPU weighted score and your GPU weighted score (scaled by resolution bias):\n"
            "`combo_score = min(cpu_score, gpu_score * bias)`\n"
            "Where `bias` is:\n"
            "- `0.7` for 1080p\n"
            "- `0.8` for 1440p (default)\n"
            "- `0.9` for 4k\n"
        )

        # Page 2: How to use, commands, data sources
        page2 = (
            "**How to add your combo:**\n"
            "Use the command:\n"
            "`{prefix}pcmr set combo <CPU Name> + <GPU Name>`\n"
            "Example:\n"
            "`{prefix}pcmr set combo Ryzen 7 5800X + RTX 3080`\n\n"
            "To remove your combo:\n"
            "`{prefix}pcmr set combo remove`\n"
            "You can view your combo with:\n"
            "`{prefix}pcmr view combo`\n"
            "Or view another member's combo:\n"
            "`{prefix}pcmr view combo @member`\n\n"
            "**Data Sources:**\n"
            "CPU scores:\n"
            "- [Single Thread](https://www.cpubenchmark.net/single-thread)\n"
            "- [Multi Thread](https://www.cpubenchmark.net/multithread)\n"
            "- [Gaming](https://www.cpubenchmark.net/top-gaming-cpus.html)\n"
            "GPU scores:\n"
            "- [3DMark Speed Way](https://www.topcpu.net/en/gpu-r/3dmark-speed-way)\n"
            "- [3DMark Time Spy Extreme](https://www.topcpu.net/en/gpu-r/3dmark-time-spy-extreme)\n"
        ).replace("{prefix}", ctx.prefix)

        embeds = [
            discord.Embed(
                title="PCMasterRace Wiki (Page 1/2)",
                description=page1,
                color=await ctx.embed_color() or DEFAULT_COLOR,
            ),
            discord.Embed(
                title="PCMasterRace Wiki (Page 2/2)",
                description=page2,
                color=await ctx.embed_color() or DEFAULT_COLOR,
            ),
        ]
        await SimpleMenu(embeds, use_select_menu=True).start(ctx)

    @pcmasterrace.command(name="compare")
    async def compare(self, ctx, *members: discord.Member):
        """
        Compare builds of multiple users (CPU, GPU, and combined).
        Usage: {prefix}pcmr compare @user1 @user2 [@user3 ...]
        If no users are provided, compares you and your combo.
        If one user is provided, compares you and that user.
        """
        # If no members provided, compare user with themselves (show their own stats)
        if not members:
            members = (ctx.author,)
        # If only one member provided, compare ctx.author and that member
        elif len(members) == 1:
            if members[0] == ctx.author:
                await ctx.send("Please mention another member to compare.")
                return
            members = (ctx.author, members[0])
        # If more than 10 members, limit for readability
        if len(members) > 10:
            await ctx.send("You can compare up to 10 users at once.")
            return

        # Gather data for all members
        user_data = []
        for member in members:
            data = await self.config.user(member).all()
            if not data["cpu"] or not data["gpu"]:
                await ctx.send(f"{member.display_name} has not submitted a combo.")
                return
            cpu_score = await self.fetch_cpu_score(data["cpu"])
            gpu_score = await self.fetch_gpu_score(data["gpu"])
            combo_score = self.combined_score(cpu_score, gpu_score)
            cpu_full = await self.regex_match(data["cpu"], self.cpu_scores.keys()) or data["cpu"]
            gpu_full = await self.regex_match(data["gpu"], self.gpu_scores.keys()) or data["gpu"]
            user_data.append({
                "member": member,
                "cpu_score": cpu_score,
                "gpu_score": gpu_score,
                "combo_score": combo_score,
                "cpu_full": cpu_full,
                "gpu_full": gpu_full,
            })

        # Sort by combined score descending
        user_data.sort(key=lambda d: d["combo_score"], reverse=True)

        # Prepare comparison description
        desc = ""
        base = user_data[0]
        for other in user_data[1:]:
            def percent(a, b):
                return (a / b) * 100 if b else 0
            cpu_percent = percent(other["cpu_score"], base["cpu_score"])
            gpu_percent = percent(other["gpu_score"], base["gpu_score"])
            combo_percent = percent(other["combo_score"], base["combo_score"])
            cpu_diff = other["cpu_score"] - base["cpu_score"]
            gpu_diff = other["gpu_score"] - base["gpu_score"]
            combo_diff = other["combo_score"] - base["combo_score"]
            desc += (
                f"**{other['member'].display_name}:**\n"
                f"CPU: **{cpu_percent:.1f}%** of {base['member'].display_name} (Δ {cpu_diff:+})\n"
                f"GPU: **{gpu_percent:.1f}%** of {base['member'].display_name} (Δ {gpu_diff:+})\n"
                f"Combined: **{combo_percent:.1f}%** of {base['member'].display_name} (Δ {combo_diff:+})\n\n"
            )
        if not desc:
            desc = "Only one user to compare."

        embed = discord.Embed(
            title="Build Comparison",
            description=desc,
            color=await ctx.embed_color() or DEFAULT_COLOR,
        )

        # Add a field for each user
        for d in user_data:
            embed.add_field(
                name=f"{d['member'].display_name}'s Build",
                value=(
                    f"CPU: `{d['cpu_full']}`\nGPU: `{d['gpu_full']}`\n"
                    f"CPU Score: **{d['cpu_score']}**\nGPU Score: **{d['gpu_score']}**\nCombined: **{d['combo_score']}**"
                ),
                inline=True,
            )

        # Prepare bar graph data
        labels = [d["member"].display_name for d in user_data]
        cpu_scores = [d["cpu_score"] for d in user_data]
        gpu_scores = [d["gpu_score"] for d in user_data]
        combo_scores = [d["combo_score"] for d in user_data]

        # Draw the bar graph
        img_bytes = draw_bar_graph(
            cpu_scores + gpu_scores + combo_scores,
            "Build Comparison",
            labels=labels * 3,
            bar_colors=(
                [0xFF6666] * len(labels) +
                [0x66FF66] * len(labels) +
                [0x6666FF] * len(labels)
            ),
            group_labels=["CPU", "GPU", "Combined"],
            group_size=len(labels),
        )

        files = []
        if img_bytes:
            file = discord.File(img_bytes, filename="compare.png")
            files = [file]
            embed.set_image(url="attachment://compare.png")

        await ctx.send(embed=embed, files=files)

def setup(bot):
    cog = PCMasterRace(bot)
    bot.add_cog(cog)
