from __future__ import annotations

import urllib.parse
from typing import Any, Dict

import discord
from core import Context, Parrot, ParrotButton, ParrotView

constant: Dict[str, str] = {
    "\N{SUPERSCRIPT ONE}": "^1",
    "\N{SUPERSCRIPT TWO}": "^2",
    "\N{SUPERSCRIPT THREE}": "^3",
    "\N{SUPERSCRIPT FOUR}": "^4",
    "\N{SUPERSCRIPT FIVE}": "^5",
    "\N{SUPERSCRIPT SIX}": "^6",
    "\N{SUPERSCRIPT SEVEN}": "^7",
    "\N{SUPERSCRIPT EIGHT}": "^8",
    "\N{SUPERSCRIPT NINE}": "^9",
    "\N{SUPERSCRIPT ZERO}": "^0",
}

CALC_BUTTONS = [
    [
        ("7", "7", "green"),
        ("8", "8", "green"),
        ("9", "9", "green"),
        ("/", "/", "blurple"),
        ("\N{SQUARE ROOT}", "sqrt(", "blurple"),
    ],
    [
        ("4", "4", "green"),
        ("5", "5", "green"),
        ("6", "6", "green"),
        ("*", "*", "blurple"),
        ("1/x", "1/", "blurple"),
    ],
    [
        ("1", "1", "green"),
        ("2", "2", "green"),
        ("3", "3", "green"),
        ("+", "+", "blurple"),
        ("%", "/100", "blurple"),
    ],
    [
        ("0", "0", "green"),
        ("00", "00", "green"),
        (".", ".", "green"),
        ("-", "-", "blurple"),
        ("=", "=", "danger"),
    ],
    [
        ("<", "back", "grey"),
        (">", "forward", "grey"),
        ("Change To Scientific", "scientific", "danger"),
    ],
]


class CalcButton(ParrotButton):
    view: CalcView

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def callback(self, interaction: discord.Interaction):
        if (self.row or 0) <= 3 and self.label != "=":
            self.arg += str(self.label)
        elif self.label == "=":
            res = await self.view.bot.http_session.get(
                f"http://twitch.center/customapi/math?expr={urllib.parse.quote(self.arg)}"
            )
            self.arg = await res.text()
        elif self.label == "Change To Scientific":
            embed = discord.Embed(
                description=f"```\n{self.arg} \n```",
            )
            await interaction.response.edit_message(
                embed=embed,
                view=ScientificCalculator(timeout=120, ctx=self.view.ctx, arg=self.arg),
            )
            return
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=f"```\n{self.arg} \n```",
            ),
            view=self.view,
        )


class CalcView(ParrotView):
    def __init__(self, *, timeout: float, ctx: Context, arg: Any = None):
        super().__init__(timeout=timeout, ctx=ctx)
        self.bot: Parrot = ctx.bot

        self.arg = arg or ""

        for i, row in enumerate(CALC_BUTTONS):
            for label, custom_id, color in row:
                btn = CalcButton(
                    label=label,
                    custom_id=custom_id,
                    style=getattr(discord.ButtonStyle, color),
                    row=i,
                    disabled=label in {"<", ">"},
                )
                self.add_item(btn)


class ScientificCalculator(ParrotView):
    def __init__(self, *, timeout: float, ctx: Context, arg: str):
        super().__init__(timeout=timeout, ctx=ctx)
        self.arg = arg or ""

    @discord.ui.button(label="C", style=discord.ButtonStyle.red, row=0)
    async def __button_c(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg = ""
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="\N{PLUS-MINUS SIGN}", style=discord.ButtonStyle.green, row=0)
    async def __button_inv(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg = f"-{self.arg}"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="ln", style=discord.ButtonStyle.green, row=0)
    async def __button_ln(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "ln("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="(", style=discord.ButtonStyle.green, row=0)
    async def __button_left_bracket(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label=")", style=discord.ButtonStyle.green, row=0)
    async def __button_right_bracket(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += ")"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    # row 1

    @discord.ui.button(label="[.]", style=discord.ButtonStyle.green, row=1)
    async def __button_gif(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "floor("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="sinh", style=discord.ButtonStyle.green, row=1)
    async def __button_sinh(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "sinh("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="sin", style=discord.ButtonStyle.green, row=1)
    async def __button_sin(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "sin("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="x\N{SUPERSCRIPT TWO}", style=discord.ButtonStyle.green, row=1)
    async def __button_x_power_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "^2"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="x!", style=discord.ButtonStyle.green, row=1)
    async def __button_factorial(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "factorial("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    # row 2

    @discord.ui.button(label="e", style=discord.ButtonStyle.green, row=2)
    async def __button_e(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "e"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="cosh", style=discord.ButtonStyle.green, row=2)
    async def __button_cosh(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "cosh("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="cos", style=discord.ButtonStyle.green, row=2)
    async def __button_cos(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "cos("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="x\N{MODIFIER LETTER SMALL Y}", style=discord.ButtonStyle.green, row=2)
    async def __button_x_power(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "^"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="\N{MODIFIER LETTER SMALL Y}\N{SQUARE ROOT}x",
        style=discord.ButtonStyle.green,
        row=2,
    )
    async def __button_x_power_1_over_y(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "^(1/"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    # row 3
    @discord.ui.button(label="\N{GREEK SMALL LETTER PI}", style=discord.ButtonStyle.green, row=3)
    async def __button_pi(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "pi"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="tanh", style=discord.ButtonStyle.green, row=3)
    async def __button_tanh(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "tanh("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="tan", style=discord.ButtonStyle.green, row=3)
    async def __button_tan(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "tan("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="x\N{SUPERSCRIPT THREE}", style=discord.ButtonStyle.green, row=3)
    async def __button_x_power_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "^3"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="\N{SUPERSCRIPT THREE}\N{SQUARE ROOT}x",
        style=discord.ButtonStyle.green,
        row=3,
    )
    async def __button_x_power_1_over_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "^(1/3)"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    # row 4
    @discord.ui.button(label="e\N{MODIFIER LETTER SMALL X}", style=discord.ButtonStyle.green, row=4)
    async def __button_e_power(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "e^"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="mod", style=discord.ButtonStyle.green, row=4)
    async def __button_mod(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "mod("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="log", style=discord.ButtonStyle.green, row=4)
    async def __button_log(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg += "log("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="10\N{MODIFIER LETTER SMALL X}", style=discord.ButtonStyle.green, row=4)
    async def __button_10_power(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.arg = f"10^{self.arg}"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.red, row=4)
    async def __button_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
        )
        await interaction.response.edit_message(
            embed=embed,
            view=CalcView(timeout=120, ctx=self.ctx, arg=self.arg),
        )
