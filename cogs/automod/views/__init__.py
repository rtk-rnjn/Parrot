from __future__ import annotations

import json
from typing import Dict, List

import discord
from discord.interactions import Interaction
from core import Context, Parrot, ParrotButton, ParrotModal, ParrotSelect, ParrotView

ACTION_PATH = "cogs/automod/templates/actions.json"

with open(ACTION_PATH, "r") as f:
    ACTIONS: Dict[str, List[Dict[str, str]]] = json.load(f)


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


def get_action_item() -> ParrotSelect:
    options = [
        discord.SelectOption(
            label=action["type"].replace("_", " ").title(),
            value=f"{action}",  # dict -> str
        )
        for action in ACTIONS["actions"]
    ]

    async def callback(self: ParrotSelect, interaction: discord.Interaction) -> None:
        assert self.view is not None

        await interaction.response.send_modal(ActionModal(data=self.view.values[0]))

    return ParrotSelect(
        placeholder="Select an action",
        options=options,
        max_values=1,
        min_values=1,
    ).set_callback(callback)


def get_text_input(*, name: str, value: str) -> discord.ui.TextInput:
    return discord.ui.TextInput(
        placeholder=f"Enter {name.replace('_', ' ').title()}",
        custom_id=f"{name}_{value}",
        label=name.replace("_", " ").title(),
    )


class ActionView(ParrotView):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(get_action_item())


class ActionModal(ParrotModal):
    def __init__(self, *, data: str, **kw) -> None:
        d: dict = json.loads(data)

        super().__init__(title=d.pop('type'), **kw)
        self.data = d

        for k in d:
            self.add_item(get_text_input(name=k, value=d[k]))

    async def on_submit(self, interaction: Interaction) -> None:
        pass
