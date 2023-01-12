import os
import time
import discord
from PIL import Image
from redbot.core import commands
from redbot.core.data_manager import bundled_data_path

from redbot.core.bot import Red

BaseCog = getattr(commands, "Cog", object)


class Longcat(BaseCog):
    def __init__(self, bot: Red):
        self.bot = bot

    # limit to 42 trunks
    catto = ["c" + "a" * i + "t" for i in range(2, 42)]
    lmao = ["lm" + "a" * i + "o" for i in range(1, 42)]
    nyan = ["ny" + "a" * i + "n" for i in range(1, 42)]
    catto.extend(lmao)
    catto.extend(nyan)

    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(attach_files=True)
    @commands.command(aliases=catto)
    async def cat(self, ctx):
        """Summon a longcat."""
        # grab the length of prefix + "lm" or "c" to exclude later
        if str(ctx.message.content.split(ctx.prefix)[1]).startswith("lm"):
            len_prefix = len(ctx.prefix) + 2
            the_cat = [Image.open(bundled_data_path(self) / "butt_oyen.png")]
            trunk = Image.open(bundled_data_path(self) / "trunk_oyen.png")
            head = Image.open(bundled_data_path(self) / "head_oyen.png")
        elif str(ctx.message.content.split(ctx.prefix)[1]).startswith("ny"):
            len_prefix = len(ctx.prefix) + 2
            the_cat = [Image.open(bundled_data_path(self) / "nyan_back.png")]
            trunk = Image.open(bundled_data_path(self) / "nyan_mid.png")
            head = Image.open(bundled_data_path(self) / "nyan_front.png")
        else:
            len_prefix = len(ctx.prefix) + 1
            the_cat = [Image.open(bundled_data_path(self) / "butt.png")]
            trunk = Image.open(bundled_data_path(self) / "trunk.png")
            head = Image.open(bundled_data_path(self) / "head.png")
        # grab length of trunks and subtract 1 for "c" or "o"
        # and substract one to length because of letter t
        len_cat = len(ctx.message.content) - len_prefix - 1

        i = 0
        while i < (len_cat):
            the_cat.append(trunk)
            i += 1
        the_cat.append(head)
        widths, heights = zip(*(i.size for i in the_cat))
        total_widths = sum(widths)
        total_heights = max(heights)
        cat = Image.new("RGBA", (total_widths, total_heights))
        x_offset = 0
        for im in the_cat:
            cat.paste(im, (x_offset, 0))
            x_offset += im.size[0]
        # I'm giving it a name based on a timestamp, this prevents future problems
        litter_box = str(time.time()).split(".")[0] + ".png"
        cat.save(bundled_data_path(self) / litter_box)
        await ctx.send(
            file=discord.File(fp=str((bundled_data_path(self) / litter_box)))
        )
        os.remove(bundled_data_path(self) / litter_box)
