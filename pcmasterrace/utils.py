import io
import json
import discord
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import re

FONT_PATH = Path(__file__).parent / "fonts" / "NotoSans.ttf"
WEIGHTS_PATH = Path(__file__).parent / "scores" / "weights.json"
CPU_SCORES_PATH = Path(__file__).parent / "scores" / "cpu.json"
GPU_SCORES_PATH = Path(__file__).parent / "scores" / "gpu.json"
WEIGHTS_PATH = Path(__file__).parent / "scores" / "weights.json"

with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
    WEIGHTS = json.load(f)

PAGE_SIZE = 10
CATEGORIES = ["CPU", "GPU", "Combined"]

DEFAULT_WEIGHT = 0
DEFAULT_COLOR = 0x5D4A84  # Default color for embeds

COMMON_WORDS = {
    "nvidia": "",
    "geforce": "",
    "radeon": "",
    "ada": "",
    "generation": "",
    "amd": "",
    "intel": "",
}


def get_page(scores, page):
    """
    Returns a dictionary of items for the specified page and the total number of pages.
    The items are sorted in descending order by their values. Pagination is applied using
    a constant PAGE_SIZE. If the scores dictionary is empty, returns an empty dictionary
    and 1 as the total number of pages.
    Args:
        scores (dict): A dictionary where keys are items and values are scores.
        page (int): The page number (0-based index) to retrieve.
    Returns:
        tuple: A tuple containing:
            - dict: The items for the requested page.
            - int: The total number of pages.
    """

    if not scores:
        return {}, 1

    items = sorted(scores.items(), key=lambda x: -x[1])
    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = items[start:end]
    return dict(page_items), total_pages


def draw_bar_graph(scores, title, page=0):
    """
    Generates a paginated horizontal bar graph image from a dictionary of scores.
    Args:
        scores (dict): A dictionary mapping labels (str) to numeric scores (int or float).
        title (str): The title to display at the top of the graph.
        page (int, optional): The page number for pagination (default is 0).
    Returns:
        io.BytesIO or None: A BytesIO object containing the PNG image of the bar graph,
            or None if there are no items to display.
    Notes:
        - The function sorts the scores in descending order and paginates the results.
        - Labels are cleaned by removing common words and wrapped if too long.
        - The bar graph is rendered using PIL, with scores displayed inside or outside bars
          depending on available space.
        - If there are multiple pages, the page number is shown in the title.
    """

    items = sorted(scores.items(), key=lambda x: -x[1])
    if not items:
        return None

    # Pagination
    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = items[start:end]

    width = 700
    bar_height = 32
    margin = 16
    label_width = 190
    spacing = 12
    label_font_size = 20
    min_label_font_size = 14
    score_font_size = 20
    title_font_size = 28
    bar_color = (70, 130, 180)
    bg_color = (30, 30, 30)
    text_color = (240, 240, 240)
    inside_text_color = (30, 30, 30)
    max_score = max(v for _, v in items)
    height = margin * 2 + len(page_items) * (bar_height + spacing) + 60

    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    font_label = ImageFont.truetype(str(FONT_PATH), label_font_size)
    font_score = ImageFont.truetype(str(FONT_PATH), score_font_size)
    title_font = ImageFont.truetype(str(FONT_PATH), title_font_size)

    # Draw title (add page info if more than one page)
    title_text = title
    if total_pages > 1:
        title_text += f" (Page {page + 1}/{total_pages})"
    draw.text((margin, margin), title_text, font=title_font, fill=text_color)
    y = margin + title_font_size + 20  # Adjusted for bigger font

    for name, value in page_items:
        # Remove words mentioned in COMMON_WORDS from label (case-insensitive)
        label = str(name)
        for word in COMMON_WORDS:
            # Remove all case variations using case-insensitive replace
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            label = pattern.sub("", label)
        label = label.strip()

        # Adjust label font size and wrap if too long
        label_font = font_label
        label_lines = [label]
        if len(label) > 18:
            # Try to split label into two lines at a space near the middle
            mid = len(label) // 2
            split_pos = label.rfind(" ", 0, mid)
            if split_pos == -1:
                split_pos = label.find(" ", mid)
            if split_pos != -1:
                label_lines = [
                    label[:split_pos].strip(),
                    label[split_pos + 1 :].strip(),
                ]
            else:
                label_lines = [label[:mid].strip(), label[mid:].strip()]
            label_font = ImageFont.truetype(str(FONT_PATH), min_label_font_size)

        if max_score == 0:
            bar_len = 0
        else:
            bar_len = int((width - label_width - margin * 2) * (value / max_score))
        draw.rectangle(
            [label_width, y, label_width + bar_len, y + bar_height],
            fill=bar_color,
        )

        # Draw label (possibly two lines)
        label_y = y + 2
        if len(label_lines) == 2:
            line_height = (bar_height - 4) // 2
            draw.text((margin, label_y), label_lines[0], font=label_font, fill=text_color)
            draw.text(
                (margin, label_y + line_height),
                label_lines[1],
                font=label_font,
                fill=text_color,
            )
        else:
            draw.text(
                (margin, label_y + (bar_height - label_font_size) // 2),
                label_lines[0],
                font=label_font,
                fill=text_color,
            )

        # Draw score inside the bar if it fits, else outside
        score_text = str(value)
        bbox = draw.textbbox((0, 0), score_text, font=font_score)
        score_w = bbox[2] - bbox[0]
        score_h = bbox[3] - bbox[1]
        score_x_inside = label_width + bar_len - score_w - 8
        score_x_outside = label_width + bar_len + 8
        score_y = y + (bar_height - score_h) // 2

        if bar_len > score_w + 16:
            draw.text(
                (score_x_inside, score_y),
                score_text,
                font=font_score,
                fill=inside_text_color,
            )
        else:
            draw.text((score_x_outside, score_y), score_text, font=font_score, fill=text_color)

        y += bar_height + spacing

    output = io.BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    return output


def build_combo_embed(
    self,
    member,
    cpu_name,
    gpu_name,
    cpu_scores,
    gpu_scores,
    embed_color=None,
    combined_score_title=None,
):
    """
    Builds a Discord embed displaying a user's CPU and GPU combo scores and details.
    Args:
        member (discord.Member): The Discord member whose combo is being displayed.
        cpu_name (str): The name of the CPU model.
        gpu_name (str): The name of the GPU model.
        cpu_scores (dict): A dictionary containing CPU score details, including a "weighted" score.
        gpu_scores (dict): A dictionary containing GPU score details, including a "weighted" score.
        embed_color (Optional[int]): The color of the embed. Defaults to a preset value if not provided.
        combined_score_title (Optional[str]): Custom title for the embed. Defaults to "<member>'s Combo" if not provided.
    Returns:
        discord.Embed: The constructed embed containing CPU and GPU information and scores.
    """

    cpu_score = next(iter(cpu_scores.values()), {}).get("weighted", 0)
    gpu_score = next(iter(gpu_scores.values()), {}).get("weighted", 0)
    cpu_details = next(iter(cpu_scores.values()), {})
    gpu_details = next(iter(gpu_scores.values()), {})
    embed = discord.Embed(
        title=combined_score_title or f"{member.display_name}'s Combo",
        color=embed_color or 0x4682B4,
        description=f"**Combined Score:** `{self.combined_score(cpu_score, gpu_score)}`",
    )
    embed.add_field(
        name="CPU",
        value=(
            f"**Model:** {next(iter(cpu_scores.keys()), cpu_name)}\n"
            f"**Weighted Score:** `{cpu_score}`\n"
            + "\n".join(
                f"• {score_name.capitalize()}: `{cpu_details.get(score_name, 0)}`"
                for score_name in cpu_details.keys()
                if score_name != "weighted"
            )
        ),
        inline=False,
    )
    embed.add_field(
        name="GPU",
        value=(
            f"**Model:** {next(iter(gpu_scores.keys()), gpu_name)}\n"
            f"**Weighted Score:** `{gpu_score}`\n"
            + "\n".join(
                f"• {score_name.capitalize()}: `{gpu_details.get(score_name, 0)}`"
                for score_name in gpu_details.keys()
                if score_name != "weighted"
            )
        ),
        inline=False,
    )
    return embed


def get_page_dict(scores, page, per_page=PAGE_SIZE):
    """
    Returns a dictionary of items for the specified page and the total number of pages.
    Args:
        scores (dict): The dictionary of items to paginate.
        page (int): The page number (0-based index).
        per_page (int, optional): Number of items per page. Defaults to PAGE_SIZE.
    Returns:
        tuple: A tuple containing:
            - dict: The items for the requested page.
            - int: The total number of pages.
    """

    items = list(scores.items())
    total_pages = (len(items) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    page_scores = dict(items[start:end])
    return page_scores, total_pages
