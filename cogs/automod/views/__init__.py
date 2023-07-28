from __future__ import annotations

import json
from typing import Any

import discord
from core import Context, ParrotModal, ParrotSelect, ParrotView
from utilities.converters import convert_bool

ACTION_PATH = "cogs/automod/templates/actions.json"
CONDITION_PATH = "cogs/automod/templates/conditions.json"
TRIGGER_PATH = "cogs/automod/templates/triggers.json"

with open(ACTION_PATH) as f:
    ACTIONS: dict[str, list[dict[str, str]]] = json.load(f)

with open(CONDITION_PATH) as f:
    CONDITIONS: dict[str, list[dict[str, str]]] = json.load(f)

with open(TRIGGER_PATH) as f:
    TRIGGERS: dict[str, list[dict[str, str]]] = json.load(f)

LIMIT = 5


def parse_dict(data: dict[str, Any]) -> str:
    data = {k: v for k, v in data.items() if v}
    return f"`{data}`"


class Automod(ParrotView):
    def __init__(self, ctx: Context, *, rule_name: str) -> None:
        super().__init__(ctx=ctx)
        self.rule_name = rule_name
        self.actions = []
        self.conditions = []
        self.triggers = []

        self.__cancelled = False
        self.add_item(get_item(self.triggers, type_="triggers"))
        self.add_item(get_item(self.conditions, type_="conditions"))
        self.add_item(get_item(self.actions, type_="actions"))

    @property
    def cancelled(self) -> bool:
        return self.__cancelled

    @property
    def embed(self) -> discord.Embed:
        return (
            discord.Embed(
                title=f"AutoMod - {self.rule_name}",
                description="Configure AutoMod for your server",
                color=discord.Color.blurple(),
            )
            .add_field(
                name="Triggers",
                value="\n".join([f"{i + 1}. {parse_dict(t)}" for i, t in enumerate(self.triggers[:5])]) or "\u200b",
                inline=False,
            )
            .add_field(
                name="Conditions",
                value="\n".join([f"{i + 1}. {parse_dict(c)}" for i, c in enumerate(self.conditions[:5])]) or "\u200b",
                inline=False,
            )
            .add_field(
                name="Actions",
                value="\n".join([f"{i + 1}. {parse_dict(a)}" for i, a in enumerate(self.actions[:5])]) or "\u200b",
                inline=False,
            )
        )

    @discord.ui.button(label="Save", style=discord.ButtonStyle.green, row=3)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not self.actions:
            return await interaction.response.send_message("Please add at least one action", ephemeral=True)

        if not self.conditions:
            return await interaction.response.send_message("Please add at least one condition. `new_message` for no condition", ephemeral=True)

        if not self.triggers:
            return await interaction.response.send_message("Please add at least one trigger", ephemeral=True)

        await interaction.response.send_message(f"{interaction.user.mention} Saved response successfully.", ephemeral=True)
        self.disable_all()
        self.stop()
        await self.message.edit(view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, row=3)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_message("Cancelled", ephemeral=True)
        self.disable_all()
        self.stop()
        self.__cancelled = True
        await self.message.edit(view=self)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.blurple, row=3)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_message("Refreshed", ephemeral=True)
        await self.message.edit(embed=self.embed)

    async def start(self) -> None:
        self.message = await self.ctx.send(embed=self.embed, view=self)


class _Parser:
    def __init__(self, value: str, method: str) -> None:
        self.value = value
        self.method = method.lower()

    def __call__(self):
        if self.method.startswith("int"):
            return self.parse_int(self.value)

        if self.method.startswith("float"):
            return self.parse_float(self.value)

        if self.method.startswith("bool"):
            return self.parse_bool(self.value)

        if self.method.startswith("list"):
            return self.parse_list(self.value)

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
        data = value.replace("<@", "").replace("<#", "").replace(">", "").replace(" ", ",").strip().split(",")
        return [i.strip() for i in data if i.strip()]


titles = {
    "actions": "Action (THEN DO THIS)",
    "conditions": "Condition (IF THIS IS TRUE)",
    "triggers": "Trigger (IF THIS HAPPENS)",
}

auto_mod_dict = {
    "triggers": TRIGGERS,
    "conditions": CONDITIONS,
    "actions": ACTIONS,
}


def get_item(main_data, *, type_: str) -> ParrotSelect:
    class Select(ParrotSelect):
        def __init__(self) -> None:
            options = [
                discord.SelectOption(
                    label=action["type"].replace("_", " ").title(),
                    value=f"{json.dumps(action)}",
                )
                for action in auto_mod_dict[type_][f"{type_}"]
            ]
            super().__init__(
                placeholder=titles[type_],
                max_values=1,
                min_values=1,
                options=options[:25],
            )

        async def callback(self, interaction: discord.Interaction) -> None:
            assert isinstance(self.view, Automod)

            if len(getattr(self.view, type_)) >= LIMIT:
                return await interaction.response.send_message("You can only add 5 items", ephemeral=True)

            data = json.loads(self.values[0])
            if len(data.keys()) == 1:
                getattr(self.view, type_).append(data)
                await interaction.response.send_message("Your response is carefully recorded", ephemeral=True)
            else:
                modal = Modal(data=self.values[0], main_data=main_data)
                await interaction.response.send_modal(modal)
                setattr(self.view, type_, main_data)

            await self.view.message.edit(embed=self.view.embed)

    return Select()


def get_text_input(*, name: str, value: str) -> discord.ui.TextInput:
    return discord.ui.TextInput(
        placeholder=f"Enter {name.replace('_', ' ').title()}",
        custom_id=f"{name}_{value}",
        label=name.replace("_", " ").title(),
    )


class Modal(ParrotModal):
    def __init__(self, *, data: str, main_data: list, **kw) -> None:  # type: ignore
        data: dict = json.loads(data)
        self.main_data = main_data
        self.__type = tp = data.pop("type")
        super().__init__(title=tp.replace("_", " ").title(), **kw)
        self.data = data

        for k in data:
            i = get_text_input(name=k, value=data[k])
            self.add_item(i)
            setattr(self, f"_I_{k}", i)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        data = {}
        for k in self.data:
            i: discord.ui.TextInput = getattr(self, f"_I_{k}")
            method = i.custom_id.split("_")[-1]
            value = i.value
            data[k] = _Parser(value, method)()

        data["type"] = self.__type
        self.main_data.append(data)
        await interaction.response.send_message("Your response is carefully recorded", ephemeral=True)
