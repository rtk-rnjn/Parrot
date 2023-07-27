from __future__ import annotations
import asyncio

import re
from io import BytesIO

import numpy as np
from PIL import Image

import discord
from core import Context

from .__constants import code_dict, codes, selector_back, selector_front


def isometric_func(shape, selector_pos=None):
    """Creates static isometric drawing."""
    t = 4
    resx = resy = 1024 * 5
    canvas = Image.new("RGBA", (resx, resy), (25, 25, 25, 0))

    shape = list(shape)
    mid = round(resx / 2)

    i = j = lvl = count = 0
    for row in shape:
        for val in row:
            fx = mid + j * t * 7 - i * t * 7
            fy = mid + j * t * 4 + i * t * 4 - lvl * t * 7
            # fx = mid + j*t*7 - i*t*7
            # fy = mid + j*t*6 + i*t*6 - lvl*t*7

            selected = False
            if [lvl, i, j] == selector_pos:
                canvas.paste(selector_back, (fx, fy), selector_back)
                selected = True

            if img := code_dict.get(val):
                canvas.paste(img, (fx, fy), img)

            if selected:
                canvas.paste(selector_front, (fx, fy), selector_front)

            j += 1
            if val == "-":
                i = -1
                j = 0
                lvl += 1

            if val in codes or selected:
                count += 1
        j = 0
        i += 1

    if count == 0:
        msg = "Did not detect any blocks. Do `j;iso blocks` or `j;help iso` to see available blocks"
        raise Exception(msg)

    canvasBox = canvas.getbbox()
    crop = canvas.crop(canvasBox)
    buf = BytesIO()
    crop.save(buf, "PNG")
    buf.seek(0)

    return buf, count


def liquid(blocks: str) -> str:
    blocks = blocks.replace("\n", " ")
    blocks = blocks.strip()
    blocks = re.sub(" +", " ", blocks)

    arr = [[[]]]
    i, j = 0, 0
    for c in blocks:
        if c not in [" ", "-"]:
            arr[i][j].append(c)

        if c == " ":
            arr[i].append([])
            j += 1

        if c == "-":
            arr.append([[]])
            i += 1
            j = 0

    arr = [list(filter(lambda x: x != [], lay)) for lay in arr]

    waters = ["2", "░", "▓", "∙"]
    lavas = ["v", "▒", "█", "·"]
    for i, lay in enumerate(arr):
        for j, row in enumerate(lay):
            for k, el in enumerate(row):
                if el == "2":
                    try:
                        if arr[i + 1][j][k] in waters:
                            arr[i][j][k] = "░"
                    except Exception:
                        pass

                elif el == "v":
                    try:
                        if arr[i + 1][j][k] in lavas:
                            arr[i][j][k] = "▒"
                    except Exception:
                        pass

    for i, lay in enumerate(arr):
        for j, row in enumerate(lay):
            for k, el in enumerate(row):
                if el == "2":
                    try:
                        if arr[i - 1][j][k] in ["░", "▓"]:
                            arr[i][j][k] = "∙"
                    except Exception:
                        pass
                elif el == "v":
                    try:
                        if arr[i - 1][j][k] in ["▒", "█"]:
                            arr[i][j][k] = "·"
                    except Exception:
                        pass
                elif el == "░":
                    try:
                        if arr[i - 1][j][k] in ["░", "▓"]:
                            arr[i][j][k] = "▓"
                    except Exception:
                        pass
                elif el == "▒":
                    try:
                        if arr[i - 1][j][k] in ["▒", "█"]:
                            arr[i][j][k] = "█"
                    except Exception:
                        pass

    res = "- ".join([" ".join(["".join(row) for row in lay]) for lay in arr])
    res = res.strip()
    return re.sub(" +", " ", res)


class BlockSelector(discord.ui.Select["Minecraft"]):
    def __init__(self, selector_pos) -> None:
        options = [
            discord.SelectOption(label="Grass Block", value="1", default=True),
            discord.SelectOption(label="Water", value="2"),
            discord.SelectOption(label="Sand Block", value="3"),
            discord.SelectOption(label="Stone Block", value="4"),
            discord.SelectOption(label="Wood Planks", value="5"),
            discord.SelectOption(label="Glass Block", value="6"),
            discord.SelectOption(label="Redstone Block", value="7"),
            discord.SelectOption(label="Brick Block", value="9"),
            discord.SelectOption(label="Iron Block", value="8"),
            discord.SelectOption(label="Gold Block", value="g"),
            discord.SelectOption(label="Diamond Block", value="d"),
            discord.SelectOption(label="Purple Block", value="p"),
            discord.SelectOption(label="Coal Block", value="c"),
            discord.SelectOption(label="Leaf Block", value="l"),
            discord.SelectOption(label="Wooden Log", value="o"),
            discord.SelectOption(label="Hay Bale", value="h"),
            discord.SelectOption(label="Poppy", value="y"),
            discord.SelectOption(label="Cake", value="k"),
            discord.SelectOption(label="Lava", value="v"),
        ]
        super().__init__(options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None

        self.view.block = self.values[0]
        for option in self.options:
            option.default = False
            if option.value == self.values[0]:
                option.default = True

        await interaction.response.edit_message(view=self.view)


class Minecraft(discord.ui.View):
    block_names = {
        "1": "Grass Block",
        "2": "Water",
        "3": "Sand Block",
        "4": "Stone Block",
        "5": "Wooden Planks",
        "6": "Glass Block",
        "7": "Redstone Block",
        "8": "Iron Block",
        "9": "Brick Block",
        "g": "Gold Block",
        "p": "Purple Block",
        "d": "Diamond Block",
        "c": "Coal Block",
        "l": "Leaf Block",
        "o": "Wooden Log",
        "h": "Hay Bale",
        "v": "Lava",
        "y": "Poppy",
        "k": "Cake",
    }

    def __init__(self, ctx: Context, shape=None, selector_pos=None) -> None:
        if shape is None:
            shape = [50, 50, 50]
        super().__init__(timeout=None)
        self.ctx = ctx
        self.box = np.zeros(shape, np.uint8).astype(str)
        self.block = "1"
        self.selector_pos = selector_pos or [i // 2 for i in shape]
        self.prev_pos = None
        self.message = None
        self.block_selector = BlockSelector(self.selector_pos)
        self.n_blocks = 0
        self.add_item(self.block_selector)

        self.selatan_btn = discord.ui.Button(
            emoji="\N{NORTH WEST ARROW}",
            style=discord.ButtonStyle.secondary,
            row=1,
        )
        self.selatan_btn.callback = self.selatan_arrow
        self.add_item(self.selatan_btn)

        self.up_btn = discord.ui.Button(
            emoji="\N{UPWARDS BLACK ARROW}",
            style=discord.ButtonStyle.secondary,
            row=1,
        )
        self.up_btn.callback = self.up_arrow
        self.add_item(self.up_btn)

        self.barat_btn = discord.ui.Button(
            emoji="\N{NORTH EAST ARROW}",
            style=discord.ButtonStyle.secondary,
            row=1,
        )
        self.barat_btn.callback = self.barat_arrow
        self.add_item(self.barat_btn)

        self.destroy_btn = discord.ui.Button(emoji="\N{PICK}", style=discord.ButtonStyle.danger, disabled=True, row=2)
        self.destroy_btn.callback = self.destroy
        self.add_item(self.destroy_btn)

        self.place_btn = discord.ui.Button(
            emoji="\N{BLACK CIRCLE FOR RECORD}",
            style=discord.ButtonStyle.success,
            row=2,
        )
        self.place_btn.callback = self.place
        self.add_item(self.place_btn)

        self.finish_btn = discord.ui.Button(
            emoji="\N{WHITE HEAVY CHECK MARK}",
            style=discord.ButtonStyle.primary,
            disabled=True,
            row=2,
        )
        self.finish_btn.callback = self.finish
        self.add_item(self.finish_btn)

        self.timur_btn = discord.ui.Button(
            emoji="\N{SOUTH WEST ARROW}",
            style=discord.ButtonStyle.secondary,
            row=3,
        )
        self.timur_btn.callback = self.timur_arrow
        self.add_item(self.timur_btn)

        self.down_btn = discord.ui.Button(
            emoji="\N{DOWNWARDS BLACK ARROW}",
            style=discord.ButtonStyle.secondary,
            row=3,
        )
        self.down_btn.callback = self.down_arrow
        self.add_item(self.down_btn)

        self.utara_btn = discord.ui.Button(
            emoji="\N{SOUTH EAST ARROW}",
            style=discord.ButtonStyle.secondary,
            row=3,
        )
        self.utara_btn.callback = self.utara_arrow
        self.add_item(self.utara_btn)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't use this button!", ephemeral=True)
            return False

        return True

    async def update(self, interaction: discord.Interaction):
        self.destroy_btn.disabled = self.box[tuple(self.selector_pos)] == "0"
        self.finish_btn.disabled = np.all(self.box == "0")  # type: ignore

        code = "- ".join([" ".join(["".join(row) for row in lay]) for lay in self.box])
        if "2" in code or "v" in code:
            code = liquid(code)

        buf, c = await asyncio.to_thread(isometric_func, code.split(), self.selector_pos)
        c -= 1
        buf_file = discord.File(buf, "interactive_iso.png")

        await interaction.response.edit_message(
            content=f"`{tuple(reversed(self.selector_pos))}::rendered {c} block{['', 's'][c > 1]}`\n\u200b",
            attachments=[buf_file],
            view=self,
        )

    async def selatan_arrow(self, interaction: discord.Interaction):
        if self.selector_pos[2] > 0:
            self.utara_btn.disabled = False
        self.selector_pos[2] -= 1
        if self.selector_pos[2] == 0:
            self.selatan_btn.disabled = True

        await self.update(interaction)

    async def up_arrow(self, interaction: discord.Interaction):
        if self.selector_pos[0] > 0:
            self.down_btn.disabled = False
        self.selector_pos[0] += 1
        if self.selector_pos[0] == self.box.shape[0] - 1:
            self.up_btn.disabled = True

        await self.update(interaction)

    async def barat_arrow(self, interaction: discord.Interaction):
        if self.selector_pos[1] > 0:
            self.timur_btn.disabled = False
        self.selector_pos[1] -= 1
        if self.selector_pos[1] == 0:
            self.barat_btn.disabled = True

        await self.update(interaction)

    async def destroy(self, interaction: discord.Interaction):
        self.box[tuple(self.selector_pos)] = "0"

        await self.update(interaction)

    async def place(self, interaction: discord.Interaction):
        self.box[tuple(self.selector_pos)] = self.block

        await self.update(interaction)

    async def finish(self, interaction: discord.Interaction):
        code = "- ".join([" ".join(["".join(row) for row in lay]) for lay in self.box])

        if "2" in code or "v" in code:
            code = liquid(code)

        buf, _ = await asyncio.to_thread(isometric_func, code.split())
        await self.ctx.reply(file=discord.File(buf, "interactive_iso.png"), mention_author=False)

        for child in self.children[:]:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(view=self)

        self.stop()

    async def timur_arrow(self, interaction: discord.Interaction):
        if self.selector_pos[1] < self.box.shape[1] - 1:
            self.barat_btn.disabled = False
        self.selector_pos[1] += 1
        if self.selector_pos[1] == self.box.shape[1] - 1:
            self.timur_btn.disabled = True

        await self.update(interaction)

    async def down_arrow(self, interaction: discord.Interaction):
        if self.selector_pos[0] < self.box.shape[0] - 1:
            self.up_btn.disabled = False
        self.selector_pos[0] -= 1
        if self.selector_pos[0] == 0:
            self.down_btn.disabled = True

        await self.update(interaction)

    async def utara_arrow(self, interaction: discord.Interaction):
        if self.selector_pos[2] < self.box.shape[2] - 1:
            self.selatan_btn.disabled = False
        self.selector_pos[2] += 1
        if self.selector_pos[2] == self.box.shape[2] - 1:
            self.utara_btn.disabled = True

        await self.update(interaction)
