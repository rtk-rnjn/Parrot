from __future__ import annotations

import json
from typing import Dict, List

import discord
from core import Context, Parrot, ParrotButton, ParrotModal, ParrotSelect, ParrotView
from utilities.converters import convert_bool

ACTION_PATH = "cogs/automod/templates/actions.json"
CONDITION_PATH = "cogs/automod/templates/conditions.json"
TRIGGER_PATH = "cogs/automod/templates/triggers.json"

with open(ACTION_PATH, "r") as f:
    ACTIONS: Dict[str, List[Dict[str, str]]] = json.load(f)

with open(CONDITION_PATH, "r") as f:
    CONDITIONS: Dict[str, List[Dict[str, str]]] = json.load(f)

with open(TRIGGER_PATH, "r") as f:
    TRIGGERS: Dict[str, List[Dict[str, str]]] = json.load(f)


class Automod(ParrotView):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx=ctx)
        self.actions = [
            # {
            #    "type": "...",
            #    "...": "...
            # }
        ]
        self.conditions = []
        self.triggers = []

        self.embed = (
            discord.Embed(title="AutoMod", description="Configure AutoMod for your server", color=discord.Color.blurple())
            .add_field(
                name="Triggers",
                value="\n".join([f"{i + 1}. {t}" for i, t in enumerate(self.triggers)]) or "\u200b",
            )
            .add_field(
                name="Conditions",
                value="\n".join([f"{i + 1}. {c}" for i, c in enumerate(self.conditions)]) or "\u200b",
            )
            .add_field(
                name="Actions",
                value="\n".join([f"{i + 1}. {a}" for i, a in enumerate(self.actions)]) or "\u200b",
            )
        )

    @discord.ui.button(label="If", style=discord.ButtonStyle.blurple, disabled=True)
    async def trigger(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(emoji="\N{HEAVY PLUS SIGN}", style=discord.ButtonStyle.green)
    async def add_trigger(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_message("Select a trigger", view=View(self.triggers, tp="trigger"))

    @discord.ui.button(emoji="\N{HEAVY MINUS SIGN}", style=discord.ButtonStyle.red)
    async def remove_trigger(self, interaction: discord.Interaction, b: discord.ui.Button) -> None:
        if not self.triggers:
            return await interaction.response.send_message("There are no triggers to remove", ephemeral=True)
        self.triggers.pop()
        await interaction.response.send_message("Your response is carefully recorded", ephemeral=True)

    @discord.ui.button(label="This", style=discord.ButtonStyle.blurple, row=1, disabled=True)
    async def condition(self, i: discord.Interaction, b: discord.ui.Button) -> None:
        pass

    @discord.ui.button(emoji="\N{HEAVY PLUS SIGN}", style=discord.ButtonStyle.green, row=1)
    async def add_condition(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_message("Select a condition", view=View(self.conditions, tp="condition"))

    @discord.ui.button(emoji="\N{HEAVY MINUS SIGN}", style=discord.ButtonStyle.red, row=1)
    async def remove_condition(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not self.conditions:
            return await interaction.response.send_message("There are no conditions to remove", ephemeral=True)
        self.conditions.pop()
        await interaction.response.send_message("Your response is carefully recorded", ephemeral=True)

    @discord.ui.button(label="Then", style=discord.ButtonStyle.blurple, row=2, disabled=True)
    async def action(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        pass

    @discord.ui.button(emoji="\N{HEAVY PLUS SIGN}", style=discord.ButtonStyle.green, row=2)
    async def add_action(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_message("Select an action", view=View(self.actions, tp="action"))

    @discord.ui.button(emoji="\N{HEAVY MINUS SIGN}", style=discord.ButtonStyle.red, row=2)
    async def remove_action(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not self.actions:
            return await interaction.response.send_message("There are no actions to remove", ephemeral=True)
        self.actions.pop()
        await interaction.response.send_message("Your response is carefully recorded", ephemeral=True)


class _Parser:
    def __init__(self, value: str, method):
        self.value = value
        self.method = method.lower()

    def __call__(self):
        if self.method.startswith("int"):
            return self.parse_int(self.value)
        elif self.method.startswith("float"):
            return self.parse_float(self.value)
        elif self.method.startswith("bool"):
            return self.parse_bool(self.value)
        elif self.method.startswith("list"):
            return self.parse_list(self.value)
        else:
            return self.value

    def parse_int(self, value: str):
        try:
            return int(value)
        except ValueError:
            pass

    def parse_float(self, value: str):
        try:
            return float(value)
        except ValueError:
            pass

    def parse_bool(self, value: str):
        convert_bool(value)

    def parse_list(self, value: str):
        return value.split(",")


titles = {
    "action": "Select an action",
    "condition": "Select a condition",
    "trigger": "Select a trigger",
}

auto_mod_dict = {
    "action": ACTIONS,
    "condition": CONDITIONS,
    "trigger": TRIGGERS,
}


def get_item(main_data, *, tp: str) -> ParrotSelect:
    options = [
        discord.SelectOption(
            label=action["type"].replace("_", " ").title(),
            value=f"{json.dumps(action)}",  # dict -> str
        )
        for action in auto_mod_dict[tp]["actions"]
    ]

    slct = ParrotSelect(
        placeholder=titles[tp or "action"],
        options=options,
        max_values=1,
        min_values=1,
    )

    async def callback(interaction: discord.Interaction) -> None:
        assert isinstance(slct.view, Automod)

        data = json.loads(slct.values[0])
        if len(data.keys()) == 1:
            slct.view.actions.append(data)
            await interaction.response.send_message("Your response is carefully recorded", ephemeral=True)
        else:
            await interaction.response.send_modal(Modal(data=slct.values[0], main_data=main_data))

    return slct.set_callback(callback)


def get_text_input(*, name: str, value: str) -> discord.ui.TextInput:
    return discord.ui.TextInput(
        placeholder=f"Enter {name.replace('_', ' ').title()}",
        custom_id=f"{name}_{value}",
        label=name.replace("_", " ").title(),
    )


class View(ParrotView):
    def __init__(self, main_data: List, *, tp: str) -> None:
        super().__init__()
        self.add_item(get_item(main_data, tp=tp))


class Modal(ParrotModal):
    def __init__(self, *, data: str, **kw) -> None:
        d: dict = json.loads(data)
        main_data: List = kw.pop("main_data")
        self.main_data = main_data
        super().__init__(title=d.pop('type'), **kw)
        self.data = d

        for k in d:
            i = get_text_input(name=k, value=d[k])
            self.add_item(i)
            setattr(self, f"_I_{k}", i)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        data = {}
        for k in self.data:
            i: discord.ui.TextInput = getattr(self, f"_I_{k}")
            method = i.custom_id.split("_")[-1]
            value = i.value
            data[k] = _Parser(value, method)()

        self.main_data.append(data)
        await interaction.response.send_message("Your response is carefully recorded", ephemeral=True)
