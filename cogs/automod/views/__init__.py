from __future__ import annotations

import json
from typing import List

import discord
from core import Context, Parrot, ParrotButton, ParrotSelect, ParrotView, ParrotModal

ACTION_PATH = "cogs/automod/templates/actions.json"

with open(ACTION_PATH, "r") as f:
    ACTIONS = json.load(f)


class Automod(ParrotView):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx=ctx)

    @discord.ui.button(label="Trigger", style=discord.ButtonStyle.blurple)
    async def trigger(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(emoji="\N{HEAVY PLUS SIGN}", style=discord.ButtonStyle.green)
    async def add_trigger(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(emoji="\N{HEAVY MINUS SIGN}", style=discord.ButtonStyle.red)
    async def remove_trigger(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(label="Condition", style=discord.ButtonStyle.blurple, row=1)
    async def condition(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(emoji="\N{HEAVY PLUS SIGN}", style=discord.ButtonStyle.green, row=1)
    async def add_condition(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(emoji="\N{HEAVY MINUS SIGN}", style=discord.ButtonStyle.red, row=1)
    async def remove_condition(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(label="Action", style=discord.ButtonStyle.blurple, row=2)
    async def action(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(emoji="\N{HEAVY PLUS SIGN}", style=discord.ButtonStyle.green, row=2)
    async def add_action(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(emoji="\N{HEAVY MINUS SIGN}", style=discord.ButtonStyle.red, row=2)
    async def remove_action(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass


def get_action_items() -> List[ParrotSelect]:
    return [
        ParrotSelect(
            placeholder="Select an action",
            options=[
                discord.SelectOption(label=action["type"].replace("_", " ").title(), value=action["type"])
                for action in ACTIONS
            ],
        )
    ]


class ActionModal(ParrotModal):
    def __init__(self) -> None:
        super().__init__()
    
        for item in get_action_items():
            self.add_item(item)
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
