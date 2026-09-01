from __future__ import annotations

import re
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .automod import Rule

if TYPE_CHECKING:
    from core.bot import Parrot

VALID_RULE_NAME = re.compile(r"^[a-z0-9_-]{1,32}$", re.IGNORECASE)

"""
# Overview
A more advanced automoderator system that supports more complex configurations than the basic automoderator.

## Intro

**Advanced Automoderator** is a more detailed and powerful system than the Basic Automoderator.

It provides greater flexibility and allows you to create more complex configurations. However, setting it up requires some time and effort.

Advanced Automoderator works using **user-configurable rules**. These rules are triggered when specific actions or conditions are met, and they can then perform specific actions in response. A collection of rules is called a **ruleset**.

You can also create **lists** to allow or deny specific words or domains. These lists can be used as **allowlists** or **denylists**.
"""


class AutomodRulesSelect(discord.ui.Select):
    def __init__(self, rules: list[Rule] | None = None):
        if not rules:
            disabled = True
            options = [
                discord.SelectOption(
                    label="No rules available",
                    description="You have not created any automod rules yet.",
                    value="no_rules",
                ),
            ]
        else:
            disabled = False
            options = [
                discord.SelectOption(
                    label=rule.name,
                    description=f"Priority: {rule.priority}, Enabled: {rule.enabled}",
                )
                for rule in rules
            ]
        super().__init__(
            placeholder="Select a rule to view or edit",
            min_values=1,
            max_values=1,
            options=options,
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        selected_rule_name = self.values[0]
        # Here you would fetch the rule details and display them to the user.
        await interaction.response.send_message(f"You selected the rule: {selected_rule_name}", ephemeral=True)


class CreateRuleButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Create New Rule",
            style=discord.ButtonStyle.primary,
            custom_id="create_rule_button",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        # Here you would handle the creation of a new rule.
        await interaction.response.send_message("Create Rule button clicked!", ephemeral=True)


class AutomodLayout(discord.ui.LayoutView):
    def __init__(self, rules: list[Rule] | None = None):
        super().__init__()

        container = discord.ui.Container(
            discord.ui.TextDisplay("## Automod"),
            discord.ui.TextDisplay(AUTOMOD_HELP.strip()),
            discord.ui.Separator(),
            discord.ui.ActionRow(AutomodRulesSelect(rules=rules)),
        )

        action_row = discord.ui.ActionRow(CreateRuleButton())
        self.add_item(container)
        self.add_item(action_row)


class Automod(commands.Cog):
    """Automod rule management."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.rules: dict[int, list[Rule]] = {}

    @commands.group(name="automod", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx: commands.Context[Parrot]) -> None:
        """Shows the help message for the automod feature."""
        view = AutomodLayout()
        await ctx.send(view=view)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Automod(bot))
