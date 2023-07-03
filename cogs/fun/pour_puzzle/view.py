from collections import namedtuple
from io import BytesIO

import discord
from utilities.converters import ToAsync

Liquid = namedtuple("Liquid", "color")

from PIL import Image, ImageDraw, ImageFont

from .levels import levels


class Bottle:
    def __init__(self, num, liquids):
        self.num = num
        self.liquids = liquids

    async def pour(self, onto):
        top = self.liquids[-1]
        for liquid in reversed(self.liquids):
            if liquid.color == top.color and not onto.is_full():
                onto.liquids.append(top)
                self.liquids.pop()
            else:
                break

    def is_full(self):
        return len(self.liquids) == 4

    def is_empty(self):
        return not self.liquids

    def is_completed(self):
        return self.is_full() and len({l.color for l in self.liquids}) == 1

    def __repr__(self):
        return f'Bottle(num={self.num}, Liquids[{", ".join(l.color for l in self.liquids)}])'


class BottleButton(discord.ui.Button["PourView"]):
    def __init__(self, bottle: Bottle, **kwargs):
        super().__init__(**kwargs)
        self.bottle = bottle

    async def callback(self, interaction: discord.Interaction):
        assert self.view

        if self.view.state == 0:
            self.disabled = True
            self.style = discord.ButtonStyle.primary
            self.view.selected = self
            for btn in self.view.children:
                if isinstance(btn, discord.ui.Button) and btn.custom_id == "cancel_btn":
                    btn.disabled = False
                    continue
                if isinstance(btn, BottleButton) and btn != self:
                    try:
                        btn.disabled = bool(
                            btn.bottle.is_full() or self.bottle.liquids[-1].color != btn.bottle.liquids[-1].color
                        )
                    except IndexError:
                        btn.disabled = False
            self.view.state = 1
            await interaction.response.edit_message(view=self.view)

        elif self.view.state == 1:
            await self.view.selected.bottle.pour(self.bottle)

            for btn in self.view.children:
                if isinstance(btn, discord.ui.Button) and btn.custom_id == "cancel_btn":
                    btn.disabled = True
                    continue
                if isinstance(btn, BottleButton):
                    btn.disabled = bool(btn.bottle.is_empty())
                    if btn == self.view.selected:
                        btn.style = discord.ButtonStyle.secondary
                    if btn.bottle.is_completed():
                        btn.style = discord.ButtonStyle.success
                        btn.disabled = True

            self.view.state = 0
            embed = self.view.msg.embeds[0]
            img_buf = await self.view.draw_image()

            img_file = discord.File(img_buf, "pour_game.png")
            embed.set_image(url="attachment://pour_game.png")

            if self.view.win_check():
                embed.description = f"Level : {self.view.level}\nYou've completed this level!"
                for btn in self.view.children:
                    if isinstance(btn, discord.ui.Button) and btn.custom_id != "exit_btn":
                        btn.disabled = True

                self.view.level += 1
                if self.view.level <= len(levels):
                    next_button = discord.ui.Button(
                        label=f"Level {self.view.level} >",
                        style=discord.ButtonStyle.success,
                        row=0,
                        custom_id="next_lvl_btn",
                    )
                    next_button.callback = self.view.next_button_callback

                    self.view.add_item(next_button)

            await interaction.response.edit_message(embed=embed, attachments=[img_file], view=self.view)


class PourView(discord.ui.View):
    font = ImageFont.truetype("extra/GothamMedium.ttf", 30)

    def __init__(self, ctx, level: int):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.level = level
        self.state = 0
        self.selected: BottleButton = None  # type: ignore
        self.msg: discord.Message = None  # type: ignore
        self.next_btn = None

        for i, bottle_data in enumerate(levels[self.level], start=1):
            bottle = Bottle(i, [Liquid(color) for color in bottle_data])
            self.add_item(
                BottleButton(
                    bottle,
                    label=i,
                    style=discord.ButtonStyle.secondary,
                    row=1 + (i - 1) // 5,
                    disabled=bool(bottle.is_empty()),
                )
            )

    @ToAsync()
    def draw_image(self):
        n_bottle = len(levels[self.level])
        img = Image.new("RGBA", (50 + 50 * n_bottle, 200), (255, 242, 161))
        draw = ImageDraw.Draw(img)

        for btn in self.children:
            if isinstance(btn, BottleButton):
                for i, liquid in enumerate(btn.bottle.liquids):
                    draw.rectangle(
                        (
                            btn.bottle.num * 50 - 20,
                            150 - i * 20,
                            16 + btn.bottle.num * 50,
                            130 - i * 20,
                        ),
                        liquid.color,
                    )
                draw.rectangle(
                    (btn.bottle.num * 50 - 20, 50, 16 + btn.bottle.num * 50, 150),
                    None,
                    "black",
                    3,
                )
                draw.text(
                    (btn.bottle.num * 50, 160),
                    str(btn.bottle.num),
                    "black",
                    self.font,
                    "mt",
                )
        draw.rectangle((0, 50, 1000, 55), (255, 242, 161))

        buf = BytesIO()
        img.save(buf, "PNG")
        buf.seek(0)

        return buf

    def win_check(self):
        checks = [
            (btn.bottle.is_completed() or btn.bottle.is_empty()) for btn in self.children if isinstance(btn, BottleButton)
        ]
        for btn in self.children:
            if isinstance(btn, BottleButton):
                checks.append(btn.bottle.is_completed() or btn.bottle.is_empty())

        return all(checks)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You can't use this button!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Exit", style=discord.ButtonStyle.danger, custom_id="exit_btn", row=0)
    async def exit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for btn in self.children:
            if isinstance(btn, discord.ui.Button):
                btn.disabled = True

        button.label = "Exited"
        await interaction.response.edit_message(view=self)

        self.stop()

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.danger, custom_id="reset_btn", row=0)
    async def reset_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.state = 0
        self.selected = None  # type: ignore

        for btn in self.children:
            if isinstance(btn, discord.ui.Button) and btn.custom_id == "cancel_btn":
                btn.disabled = True
                continue
            if isinstance(btn, BottleButton):
                self.remove_item(btn)

        for btn in self.children[:]:
            if isinstance(btn, BottleButton):
                self.remove_item(btn)

        for i, bottle_data in enumerate(levels[self.level], start=1):
            bottle = Bottle(i, [Liquid(color) for color in bottle_data])
            self.add_item(
                BottleButton(
                    bottle,
                    label=i,
                    style=discord.ButtonStyle.secondary,
                    row=1 + (i - 1) // 5,
                    disabled=bool(bottle.is_empty()),
                )
            )

        embed = self.msg.embeds[0]
        img_buf = await self.draw_image()

        img_file = discord.File(img_buf, "pour_game.png")
        embed.set_image(url="attachment://pour_game.png")

        await interaction.response.edit_message(embed=embed, attachments=[img_file], view=self)

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.primary,
        custom_id="cancel_btn",
        disabled=True,
        row=0,
    )
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.state != 1:
            return
        for btn in self.children:
            if isinstance(btn, BottleButton):
                btn.disabled = bool(btn.bottle.is_empty())
                if btn == self.selected:
                    btn.style = discord.ButtonStyle.secondary
                if btn.bottle.is_completed():
                    btn.disabled = True

        button.disabled = True
        self.selected = None  # type: ignore
        self.state = 0
        await interaction.response.edit_message(view=self)

    async def next_button_callback(self, interaction: discord.Interaction):
        self.state = 0
        self.selected = None  # type: ignore

        for btn in self.children[:]:
            if isinstance(btn, discord.ui.Button):
                if isinstance(btn, BottleButton) or btn.custom_id == "next_lvl_btn":
                    self.remove_item(btn)
                elif btn.custom_id == "cancel_btn":
                    btn.disabled = True
                    continue
                elif btn.custom_id in ["reset_btn", "exit_btn"]:
                    btn.disabled = False
                    continue

        for i, bottle_data in enumerate(levels[self.level], start=1):
            bottle = Bottle(i, [Liquid(color) for color in bottle_data])
            self.add_item(
                BottleButton(
                    bottle,
                    label=i,
                    style=discord.ButtonStyle.secondary,
                    row=1 + (i - 1) // 5,
                    disabled=bool(bottle.is_empty()),
                )
            )

        embed = self.msg.embeds[0]
        embed.description = f"Level : {self.level}"
        img_buf = await self.draw_image()
        img_file = discord.File(img_buf, "pour_game.png")

        embed.set_image(url="attachment://pour_game.png")
        await interaction.response.edit_message(embed=embed, attachments=[img_file], view=self)
