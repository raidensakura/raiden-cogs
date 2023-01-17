import io
import random
import time

import discord
from PIL import Image
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.data_manager import bundled_data_path


class Longcat(commands.Cog):
    """
    Summon variably-lengthed, randomly-colored longcats.
    Can be summoned with `lmao`, `cat` and `nyan`.
    """

    def __init__(self, bot: Red):
        self.bot = bot

    # limit to 42 trunks
    catto = ["c" + "a" * i + "t" for i in range(2, 42)]
    lmao = ["lm" + "a" * i + "o" for i in range(1, 42)]
    nyan = ["ny" + "a" * i + "n" for i in range(1, 42)]

    alias_list = catto + lmao + nyan

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(attach_files=True)
    @commands.command(aliases=alias_list)
    async def cat(self, ctx):
        """Summon a longcat. Can also be summoned with `nyan` or `lmao`"""

        def randomColor():
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            a = 255
            return (r, g, b, a)

        # b for bottom, t for trunk and h for head
        def fetchColor(t, b, h, trulyRGB):
            color = randomColor()
            if trulyRGB:
                # colors of bottom, trunk and head will be mismatched
                b_overlay = Image.new(size=t.size, color=randomColor(), mode="RGBA")
                t_overlay = Image.new(size=b.size, color=randomColor(), mode="RGBA")
                h_overlay = Image.new(size=h.size, color=randomColor(), mode="RGBA")
            else:
                b_overlay = Image.new(size=t.size, color=color, mode="RGBA")
                t_overlay = Image.new(size=b.size, color=color, mode="RGBA")
                h_overlay = Image.new(size=h.size, color=color, mode="RGBA")
            return b_overlay, t_overlay, h_overlay

        def fetchFilter():
            b_base = Image.open(bundled_data_path(self) / "bottom.png")
            t_base = Image.open(bundled_data_path(self) / "trunk.png")
            h_base = Image.open(bundled_data_path(self) / "head.png")
            b_outline = Image.open(bundled_data_path(self) / "bottom_outline.png")
            t_outline = Image.open(bundled_data_path(self) / "trunk_outline.png")
            h_outline = Image.open(bundled_data_path(self) / "head_outline.png")
            return b_base, t_base, h_base, b_outline, t_outline, h_outline

        def applyFilter(trulyRGB):
            b_base, t_base, h_base, b_outline, t_outline, h_outline = fetchFilter()
            b_color, t_color, h_color = fetchColor(b_base, t_base, h_base, trulyRGB)

            b_base.paste(b_color, None, mask=b_base)
            t_base.paste(t_color, None, mask=t_base)
            h_base.paste(h_color, None, mask=h_base)

            b_base.paste(b_outline, None, mask=b_outline)
            t_base.paste(t_outline, None, mask=t_outline)
            h_base.paste(h_outline, None, mask=h_outline)
            return [b_base], t_base, h_base

        def rainbowTrunks(t):
            t_base = Image.open(bundled_data_path(self) / "trunk.png")
            t_color = Image.new(size=t.size, color=randomColor(), mode="RGBA")
            t_outline = Image.open(bundled_data_path(self) / "trunk_outline.png")
            t_base.paste(t_color, None, mask=t_base)
            t_base.paste(t_outline, None, mask=t_outline)
            return t_base

        trulyRGB = False
        # grab the length of prefix + letters for bottom
        if str(ctx.message.content.lower().split(ctx.prefix)[1]).startswith("lm"):
            len_prefix = len(ctx.prefix) + 2
            trulyRGB = True
            the_cat, trunk, head = applyFilter(trulyRGB)
        elif str(ctx.message.content.lower().split(ctx.prefix)[1]).startswith("ny"):
            len_prefix = len(ctx.prefix) + 2
            the_cat = [Image.open(bundled_data_path(self) / "nyan_back.png")]
            trunk = Image.open(bundled_data_path(self) / "nyan_mid.png")
            head = Image.open(bundled_data_path(self) / "nyan_front.png")
        else:
            len_prefix = len(ctx.prefix) + 1
            the_cat, trunk, head = applyFilter(trulyRGB=False)
        # grab length of trunks and subtract 1 for head letter
        len_cat = len(ctx.message.content) - len_prefix - 1

        i = 0
        while i < (len_cat):
            if trulyRGB:
                trunk = rainbowTrunks(trunk)
            the_cat.append(trunk)
            i += 1
        the_cat.append(head)
        widths, heights = zip(*(i.size for i in the_cat))
        cat = Image.new("RGBA", (sum(widths), max(heights)))
        x_offset = 0
        for im in the_cat:
            cat.paste(im, (x_offset, 0))
            x_offset += im.size[0]
        # I'm giving it a name based on a timestamp, this prevents future problems
        litter_box = str(time.time()).split(".")[0] + ".png"
        with io.BytesIO() as image_binary:
            cat.save(image_binary, "PNG", optimize=True, quality=95)
            image_binary.seek(0)
            await ctx.send(file=discord.File(fp=image_binary, filename=litter_box))
