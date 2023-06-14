from __future__ import annotations

import urllib.parse
from typing import Any, Dict

import discord
from core import Context, Parrot

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


class CalculatorView(discord.ui.View):
    def __init__(
        self, user: discord.Member, *, timeout: float, ctx: Context, arg: Any = None
    ):
        super().__init__(timeout=timeout)
        self.user: discord.Member = user
        self.ctx: Context = ctx
        self.bot: Parrot = ctx.bot

        self.arg = arg or ""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You can not interact.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="7", style=discord.ButtonStyle.green, row=0)
    async def __button_7(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "7"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="8", style=discord.ButtonStyle.green, row=0)
    async def __button_8(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "8"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="9", style=discord.ButtonStyle.green, row=0)
    async def __button_9(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "9"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="/", style=discord.ButtonStyle.blurple, row=0)
    async def __button_divide(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "/"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="\N{SQUARE ROOT}", style=discord.ButtonStyle.blurple, row=0
    )
    async def __button_sqrt(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "sqrt("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="4", style=discord.ButtonStyle.green, row=1)
    async def __button_4(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "4"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="5", style=discord.ButtonStyle.green, row=1)
    async def __button_5(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "5"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="6", style=discord.ButtonStyle.green, row=1)
    async def __button_6(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "6"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="\N{MULTIPLICATION SIGN}", style=discord.ButtonStyle.blurple, row=1
    )
    async def __button_multiply(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "*"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="1/x", style=discord.ButtonStyle.blurple, row=1)
    async def __button_1_divide(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg = f"1/({self.arg})"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="1", style=discord.ButtonStyle.green, row=2)
    async def __button_1(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "1"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="2", style=discord.ButtonStyle.green, row=2)
    async def __button_2(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "2"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="3", style=discord.ButtonStyle.green, row=2)
    async def __button_3(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "3"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="+", style=discord.ButtonStyle.blurple, row=2)
    async def __button_plus(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "+"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="%", style=discord.ButtonStyle.blurple, row=2)
    async def __button_percent(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg = f"{self.arg}/100"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="0", style=discord.ButtonStyle.green, row=3)
    async def __button_0(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "0"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="00", style=discord.ButtonStyle.green, row=3)
    async def __button_00(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "00"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label=".", style=discord.ButtonStyle.green, row=3)
    async def __button_dot(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "."
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="-", style=discord.ButtonStyle.blurple, row=3)
    async def __button_minus(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "-"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="=", style=discord.ButtonStyle.red, row=3)
    async def __button_equal(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        res = await self.ctx.bot.http_session.get(
            f"http://twitch.center/customapi/math?expr={urllib.parse.quote(self.arg)}"
        )
        self.arg = await res.text()
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="\N{HEAVY LEFT-POINTING ANGLE QUOTATION MARK ORNAMENT}",
        style=discord.ButtonStyle.red,
        row=4,
        disabled=True,
    )
    async def __button_previous(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        ...

    @discord.ui.button(
        label="\N{HEAVY RIGHT-POINTING ANGLE QUOTATION MARK ORNAMENT}",
        style=discord.ButtonStyle.red,
        row=4,
        disabled=True,
    )
    async def __button_next(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        ...

    @discord.ui.button(
        label="Change to Scientific Calculator", style=discord.ButtonStyle.red, row=4
    )
    async def __button_scientific(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(
            embed=embed,
            view=ScientificCalculator(
                self.user, timeout=120, ctx=self.ctx, arg=self.arg
            ),
        )


class ScientificCalculator(discord.ui.View):
    def __init__(self, user: discord.Member, *, timeout: float, ctx: Context, arg: str):
        super().__init__(timeout=120)
        self.user = user
        self.ctx = ctx

        self.arg = arg or ""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "You can not interact.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="C", style=discord.ButtonStyle.red, row=0)
    async def __button_c(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg = ""
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="\N{PLUS-MINUS SIGN}", style=discord.ButtonStyle.green, row=0
    )
    async def __button_inv(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg = f"-{self.arg}"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="ln", style=discord.ButtonStyle.green, row=0)
    async def __button_ln(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "ln("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="(", style=discord.ButtonStyle.green, row=0)
    async def __button_left_bracket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label=")", style=discord.ButtonStyle.green, row=0)
    async def __button_right_bracket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += ")"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    # row 1

    @discord.ui.button(label="[.]", style=discord.ButtonStyle.green, row=1)
    async def __button_gif(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "floor("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="sinh", style=discord.ButtonStyle.green, row=1)
    async def __button_sinh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "sinh("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="sin", style=discord.ButtonStyle.green, row=1)
    async def __button_sin(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "sin("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="x\N{SUPERSCRIPT TWO}", style=discord.ButtonStyle.green, row=1
    )
    async def __button_x_power_2(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "^2"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="x!", style=discord.ButtonStyle.green, row=1)
    async def __button_factorial(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "factorial("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    # row 2

    @discord.ui.button(label="e", style=discord.ButtonStyle.green, row=2)
    async def __button_e(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "e"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="cosh", style=discord.ButtonStyle.green, row=2)
    async def __button_cosh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "cosh("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="cos", style=discord.ButtonStyle.green, row=2)
    async def __button_cos(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "cos("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="x\N{MODIFIER LETTER SMALL Y}", style=discord.ButtonStyle.green, row=2
    )
    async def __button_x_power(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "^"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="\N{MODIFIER LETTER SMALL Y}\N{SQUARE ROOT}x",
        style=discord.ButtonStyle.green,
        row=2,
    )
    async def __button_x_power_1_over_y(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "^(1/"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    # row 3
    @discord.ui.button(
        label="\N{GREEK SMALL LETTER PI}", style=discord.ButtonStyle.green, row=3
    )
    async def __button_pi(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "pi"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="tanh", style=discord.ButtonStyle.green, row=3)
    async def __button_tanh(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "tanh("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="tan", style=discord.ButtonStyle.green, row=3)
    async def __button_tan(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "tan("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="x\N{SUPERSCRIPT THREE}", style=discord.ButtonStyle.green, row=3
    )
    async def __button_x_power_3(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "^3"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="\N{SUPERSCRIPT THREE}\N{SQUARE ROOT}x",
        style=discord.ButtonStyle.green,
        row=3,
    )
    async def __button_x_power_1_over_3(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "^(1/3)"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    # row 4
    @discord.ui.button(
        label="e\N{MODIFIER LETTER SMALL X}", style=discord.ButtonStyle.green, row=4
    )
    async def __button_e_power(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "e^"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="mod", style=discord.ButtonStyle.green, row=4)
    async def __button_mod(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "mod("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="log", style=discord.ButtonStyle.green, row=4)
    async def __button_log(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg += "log("
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="10\N{MODIFIER LETTER SMALL X}", style=discord.ButtonStyle.green, row=4
    )
    async def __button_10_power(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.arg = f"10^{self.arg}"
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.red, row=4)
    async def __button_back(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        embed = discord.Embed(
            description=f"```\n{self.arg} \n```",
            color=self.ctx.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        await interaction.response.edit_message(
            embed=embed,
            view=CalculatorView(self.user, timeout=120, ctx=self.ctx, arg=self.arg),
        )
