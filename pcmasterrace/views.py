import discord
from .utils import get_page, draw_bar_graph, get_page_dict, DEFAULT_COLOR


class TabButton(discord.ui.Button):
    def __init__(self, label, tab_name, author, style=discord.ButtonStyle.secondary):
        super().__init__(label=label, style=style, custom_id=f"tab_{tab_name}")
        self.tab_name = tab_name
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This button isn't for you.", ephemeral=True)
            return

        view = self.view
        view.tab = self.tab_name
        view.page = 0
        if hasattr(view, "update_tab_styles"):
            view.update_tab_styles()
        await view.update_message(interaction)


class PageButton(discord.ui.Button):
    def __init__(self, label, delta, author, style=discord.ButtonStyle.secondary, row=1):
        super().__init__(label=label, style=style, custom_id=f"page_{label.lower()}", row=row)
        self.delta = delta
        self.author = author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This button isn't for you.", ephemeral=True)
            return

        view = self.view
        if hasattr(view, "get_scores"):
            scores = view.get_scores()
            _, total_pages = get_page_dict(scores, 0, getattr(view, "per_page", 10))
            view.page = max(0, min(view.page + self.delta, total_pages - 1))
            await view.update_message(interaction)
        elif hasattr(view, "total_pages"):
            view.page = max(0, min(view.page + self.delta, view.total_pages - 1))
            await view.update_message(interaction)


def update_tab_styles(view, tab_buttons, tab_map, active_tab):
    for i, btn in enumerate(tab_buttons):
        btn.style = (
            discord.ButtonStyle.primary
            if active_tab == list(tab_map.keys())[i]
            else discord.ButtonStyle.secondary
        )


def make_tab_buttons(tabs, author):
    return [TabButton(label=tab.upper(), tab_name=tab, author=author) for tab in tabs]


def make_pagination_buttons(author, style=discord.ButtonStyle.secondary, row=1):
    return [
        PageButton("5 ⏮️", -5, author, style, row),
        PageButton("⏪", -1, author, style, row),
        PageButton("⏩", 1, author, style, row),
        PageButton("⏭️ 5", 5, author, style, row),
    ]


async def update_scores_message(
    interaction,
    ctx,
    scores,
    page,
    total_pages,
    title,
    embed_image_name,
    view,
    color=DEFAULT_COLOR,
):
    page_scores, total_pages = (
        get_page(scores, page)
        if isinstance(scores, list)
        else get_page_dict(scores, page, getattr(view, "per_page", 10))
    )
    embed_title = f"{title} (Page {page + 1}/{total_pages})"
    img_bytes = draw_bar_graph(page_scores, embed_title)
    embed = discord.Embed(title=embed_title, color=await ctx.embed_color() or color)
    files = []
    if img_bytes:
        file = discord.File(img_bytes, filename=embed_image_name)
        files = [file]
        embed.set_image(url=f"attachment://{embed_image_name}")

    view.prev_button.disabled = page == 0
    view.next_button.disabled = page >= total_pages - 1
    view.prev5_button.disabled = page == 0
    view.next5_button.disabled = page >= total_pages - 1
    if hasattr(view, "update_tab_styles"):
        view.update_tab_styles()
    await interaction.response.edit_message(embed=embed, view=view, attachments=files)


class ScoreView(discord.ui.View):
    def __init__(self, ctx, gpu_scores, cpu_scores):
        super().__init__(timeout=120)
        self.gpu_scores = gpu_scores
        self.cpu_scores = cpu_scores
        self.tab = "cpu"
        self.page = 0
        self.ctx = ctx
        _, self.total_pages = get_page(self.gpu_scores, 0)

        self.tab_buttons = make_tab_buttons(["cpu", "gpu"], ctx.author)
        for btn in self.tab_buttons:
            self.add_item(btn)

        pagination_buttons = make_pagination_buttons(ctx.author, discord.ButtonStyle.gray, row=1)
        self.prev5_button, self.prev_button, self.next_button, self.next5_button = pagination_buttons
        for btn in pagination_buttons:
            self.add_item(btn)

        self.update_tab_styles()

    def update_tab_styles(self):
        tab_map = {"cpu": 0, "gpu": 1}
        update_tab_styles(self, self.tab_buttons, tab_map, self.tab)

    async def update_message(self, interaction):
        scores = self.gpu_scores if self.tab == "gpu" else self.cpu_scores
        title = "GPU Scores" if self.tab == "gpu" else "CPU Scores"
        await update_scores_message(
            interaction,
            self.ctx,
            scores,
            self.page,
            self.total_pages,
            title,
            "scores.png",
            self,
            DEFAULT_COLOR,
        )

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=None)
        except Exception:
            pass


class UserScoreView(discord.ui.View):
    def __init__(self, ctx, cpu_scores, gpu_scores, combined_scores):
        super().__init__(timeout=120)
        self.cpu_scores = cpu_scores
        self.gpu_scores = gpu_scores
        self.combined_scores = combined_scores
        self.page = 0
        self.ctx = ctx
        self.tab = "cpu"
        self.message = None
        self.per_page = 10

        self.tab_buttons = make_tab_buttons(["cpu", "gpu", "combined"], ctx.author)
        for btn in self.tab_buttons:
            self.add_item(btn)

        pagination_buttons = make_pagination_buttons(ctx.author, discord.ButtonStyle.secondary, row=1)
        self.prev5_button, self.prev_button, self.next_button, self.next5_button = pagination_buttons
        for btn in pagination_buttons:
            self.add_item(btn)

        self.update_tab_styles()

    def update_tab_styles(self):
        tab_map = {"cpu": 0, "gpu": 1, "combined": 2}
        update_tab_styles(self, self.tab_buttons, tab_map, self.tab)

    def get_scores(self):
        if self.tab == "cpu":
            return self.cpu_scores
        elif self.tab == "gpu":
            return self.gpu_scores
        else:
            return self.combined_scores

    async def update_message(self, interaction):
        scores = self.get_scores()
        title = f"{self.tab.upper()} Scores"
        await update_scores_message(
            interaction,
            self.ctx,
            scores,
            self.page,
            None,
            title,
            "userscores.png",
            self,
            DEFAULT_COLOR,
        )

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            if self.message:
                await self.message.edit(view=None)
        except Exception:
            pass
