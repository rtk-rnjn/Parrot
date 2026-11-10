from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from functools import partial
from typing import TYPE_CHECKING, Literal, Protocol, overload

import discord

from core.utils import BaseLayoutView

from .condition import CONDITION_GROUP, CONDITION_GROUP_NAMES, Condition, ConditionConfig, ConditionType, get_condition_modal
from .condition import CONFLICTS as CONDITION_CONFLICTS
from .condition import NoConfig as ConditionNoConfig
from .condition import describe as describe_condition
from .constants import MAX_EFFECTS
from .effect import CONFLICTS as EFFECT_CONFLICTS
from .effect import EFFECT_GROUP, EFFECT_GROUP_NAMES, Effect, EffectConfig, EffectType, get_effect_modal
from .effect import REPEATABLE as REPEATABLE_EFFECTS
from .effect import NoConfig as EffectNoConfig
from .effect import describe as describe_effect
from .rule import Rule
from .trigger import TRIGGER_GROUP, TRIGGER_GROUP_NAMES, Trigger, TriggerConfig, TriggerType, get_config_modal
from .trigger import NoConfig as TriggerNoConfig
from .trigger import describe as describe_trigger

type ItemLiteral = Literal["trigger", "condition", "effect"]
type Item = Trigger | Condition | Effect
type ItemType = TriggerType | ConditionType | EffectType
type ItemConfig = TriggerConfig | ConditionConfig | EffectConfig


@dataclass(frozen=True, slots=True)
class Catalog[E: StrEnum, Rule: ItemType, Config: ItemConfig]:
    enum: type[E]
    prompt: str
    groups: dict[str, list[E]]
    group_names: dict[str, dict[str, str]]
    empty: Config
    modal: Callable[[Rule, Callable[...]], discord.ui.Modal | None]
    describe: Callable[..., str]


CATALOGS: dict[ItemLiteral, Catalog] = {
    "trigger": Catalog(
        enum=TriggerType,
        prompt="Choose a trigger",
        groups=TRIGGER_GROUP,
        group_names=TRIGGER_GROUP_NAMES,
        modal=get_config_modal,
        empty=TriggerNoConfig(),
        describe=describe_trigger,
    ),
    "condition": Catalog(
        enum=ConditionType,
        prompt="Add a condition",
        groups=CONDITION_GROUP,
        group_names=CONDITION_GROUP_NAMES,
        modal=get_condition_modal,
        empty=ConditionNoConfig(),
        describe=describe_condition,
    ),
    "effect": Catalog(
        enum=EffectType,
        prompt="Add an effect",
        groups=EFFECT_GROUP,
        group_names=EFFECT_GROUP_NAMES,
        modal=get_effect_modal,
        empty=EffectNoConfig(),
        describe=describe_effect,
    ),
}


def pretty(item: StrEnum) -> str:
    return item.value.replace("_", " ").title()


def short_doc(item: StrEnum) -> str | None:
    LIMIT = 100
    doc = (item.__doc__ or "").strip()
    if not doc:
        return None
    return doc if len(doc) <= LIMIT else doc[:99] + "\N{HORIZONTAL ELLIPSIS}"


def merge[Item: Condition | Effect, ItemType: ConditionType | EffectType](
    items: list[Item],
    new: Item,
    *,
    repeatable: set[ItemType],
    conflicts: dict[ItemType, set[ItemType]],
) -> list[Item]:
    if new.type in repeatable:
        kept = [item for item in items if item != new]
    else:
        dropped = {new.type, *conflicts[new.type]} if new.type in conflicts else {new.type}  # pyright: ignore[reportArgumentType]

        kept = [item for item in items if item.type not in dropped]
    return [*kept, new]


def selected_value(interaction: discord.Interaction[discord.Client]) -> str:
    assert interaction.data is not None
    return interaction.data["values"][0]  # pyright: ignore[reportGeneralTypeIssues]


class SettingsModal(discord.ui.Modal):
    def __init__(self, builder: RuleBuilderView) -> None:
        super().__init__(title="Rule Settings")
        self.builder = builder

        self.name_input = discord.ui.TextInput(default=builder.rule_name, max_length=100)
        self.priority_input = discord.ui.TextInput(default=str(builder.priority), max_length=5)
        self.enabled_input = discord.ui.Checkbox(default=builder.enabled)

        self.add_item(discord.ui.Label(text="Name", component=self.name_input))
        self.add_item(
            discord.ui.Label(
                text="Priority",
                description="Higher priority rules are evaluated first.",
                component=self.priority_input,
            )
        )
        self.add_item(discord.ui.Label(text="Enabled", component=self.enabled_input))

    async def on_submit(self, interaction: discord.Interaction[discord.Client]) -> None:
        name = self.name_input.value.strip()
        if not name:
            await interaction.response.send_message("**Name** can't be empty.", ephemeral=True)
            return

        try:
            priority = int(self.priority_input.value.strip())
        except ValueError:
            await interaction.response.send_message("**Priority** must be a whole number.", ephemeral=True)
            return

        self.builder.rule_name = name
        self.builder.priority = priority
        self.builder.enabled = bool(self.enabled_input.value)
        self.builder.show_overview()
        await interaction.response.edit_message(view=self.builder)


class ButtonCallback(Protocol):
    async def __call__(self, interaction: discord.Interaction[discord.Client]) -> None: ...


class RuleBuilderView(BaseLayoutView):
    def __init__(
        self,
        author: discord.Member,
        name: str,
        *,
        on_save: Callable[[discord.Interaction[discord.Client], Rule], Awaitable[None]],
        on_cancel: Callable[[discord.Interaction[discord.Client]], Awaitable[None]],
        check_name: Callable[[str], Awaitable[str | None]] | None = None,
        rule: Rule | None = None,
    ) -> None:
        super().__init__(author=author)
        self.author = author
        self.message: discord.Message

        self.save_handler = on_save
        self.cancel_handler = on_cancel
        self.check_name = check_name
        self.editing = rule is not None

        self.rule_name = name
        self.priority = rule.priority if rule else 0
        self.enabled = rule.enabled if rule else True
        self.trigger: Trigger | None = rule.trigger if rule else None
        self.conditions: list[Condition] = list(rule.conditions) if rule else []
        self.effects: list[Effect] = list(rule.effects) if rule else []

        self.kind: ItemLiteral = "trigger"
        self.group = ""

        self.container = discord.ui.Container()
        self.show_overview()
        self.add_item(self.container)

    @property
    def ready(self) -> bool:
        return self.trigger is not None and bool(self.effects)

    def _status(self) -> str:
        if self.trigger is None:
            return "\N{WARNING SIGN} Pick a trigger"
        if not self.effects:
            return "\N{WARNING SIGN} Add an effect"
        return "\N{WHITE HEAVY CHECK MARK} Ready to save"

    def _button(
        self,
        label: str,
        callback: ButtonCallback,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        *,
        emoji: str | None = None,
        disabled: bool = False,
    ) -> discord.ui.Button[RuleBuilderView]:
        button = discord.ui.Button[RuleBuilderView](label=label, style=style, emoji=emoji, disabled=disabled)
        button.callback = callback
        return button

    def _line(self, kind: ItemLiteral, item: Trigger | Condition | Effect, prefix: str) -> str:
        detail = CATALOGS[kind].describe(item.config)
        return f"{prefix} **{pretty(item.type)}**" + (f" - {detail}" if detail else "")

    def _items(self, kind: Literal["condition", "effect"]) -> list[Condition] | list[Effect]:
        return self.conditions if kind == "condition" else self.effects

    def _added_types(self) -> set[ItemType]:
        match self.kind:
            case "trigger":
                return {self.trigger.type} if self.trigger else set()
            case "condition":
                return {item.type for item in self.conditions}
            case _:
                return {item.type for item in self.effects}

    def _add_list_block(
        self,
        kind: Literal["condition", "effect"],
        heading: str,
        empty: str,
        lines: list[str],
        *,
        noun: str,
        disabled: bool = False,
    ) -> None:
        body = "\n".join(lines) if lines else empty
        self.container.add_item(discord.ui.Separator())
        self.container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay(f"### {heading}\n{body}"),
                accessory=self._button(
                    "Add",
                    partial(self.open_picker, kind),
                    discord.ButtonStyle.secondary if lines else discord.ButtonStyle.primary,
                    disabled=disabled,
                ),
            )
        )

        items = self._items(kind)
        if items:
            remove_select = discord.ui.Select[RuleBuilderView](
                placeholder=f"Remove {noun}...",
                options=[discord.SelectOption(label=f"{index + 1}. {pretty(item.type)}"[:100], value=str(index)) for index, item in enumerate(items)],
            )
            remove_select.callback = partial(self.remove_item, kind)
            self.container.add_item(discord.ui.ActionRow(remove_select))

    def show_overview(self) -> None:
        container = self.container
        container.clear_items()
        container.accent_colour = discord.Colour.green() if self.ready else discord.Colour.orange()

        state = "Enabled" if self.enabled else "Disabled"
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay(f"# {self.rule_name}"),
                discord.ui.TextDisplay(f"-# {state} \N{MIDDLE DOT} Priority {self.priority} \N{MIDDLE DOT} {self._status()}"),
                accessory=self._button("Settings", self.settings_callback),
            )
        )

        container.add_item(discord.ui.Separator())
        trigger_body = self._line("trigger", self.trigger, "\N{BULLET}") if self.trigger else "*Not set. Pick what activates this rule.*"
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay(f"### \N{HIGH VOLTAGE SIGN} Trigger\n{trigger_body}"),
                accessory=self._button(
                    "Change" if self.trigger else "Set trigger",
                    partial(self.open_picker, "trigger"),
                    discord.ButtonStyle.secondary if self.trigger else discord.ButtonStyle.primary,
                ),
            )
        )

        self._add_list_block(
            "condition",
            "\N{DIRECT HIT} Conditions",
            "*None. The rule applies everywhere.*",
            [self._line("condition", item, "\N{BULLET}") for item in self.conditions],
            noun="a condition",
        )
        self._add_list_block(
            "effect",
            "\N{HAMMER AND WRENCH} Effects",
            "*None. Add at least one action.*",
            [self._line("effect", item, f"{index + 1}.") for index, item in enumerate(self.effects)],
            noun="an effect",
            disabled=len(self.effects) >= MAX_EFFECTS,
        )

        container.add_item(discord.ui.Separator())
        container.add_item(
            discord.ui.ActionRow(
                self._button(
                    "Save rule",
                    self.save_callback,
                    discord.ButtonStyle.success,
                    emoji="\N{FLOPPY DISK}",
                    disabled=not self.ready,
                ),
                self._button("Cancel", self.cancel_callback, discord.ButtonStyle.danger),
            )
        )

    def show_picker(self) -> None:
        catalog = CATALOGS[self.kind]
        info = catalog.group_names[self.group]
        added = self._added_types()

        container = self.container
        container.clear_items()
        container.accent_colour = discord.Colour.blurple()

        container.add_item(discord.ui.TextDisplay(f"## {catalog.prompt}"))
        container.add_item(discord.ui.TextDisplay(f"**{info['name']}** - {info['description']}"))
        container.add_item(discord.ui.Separator(visible=False))

        container.add_item(
            discord.ui.ActionRow(
                *(
                    self._button(
                        catalog.group_names[group]["name"],
                        partial(self.pick_group, group),
                        discord.ButtonStyle.primary if group == self.group else discord.ButtonStyle.secondary,
                        emoji=catalog.group_names[group]["emoji"],
                    )
                    for group in catalog.groups
                )
            )
        )

        item_select = discord.ui.Select[RuleBuilderView](
            placeholder=f"Select from {info['name']}...",
            options=[
                discord.SelectOption(
                    label=("\N{WHITE HEAVY CHECK MARK}" if item in added else "") + pretty(item),
                    description=short_doc(item),
                    value=item.value,
                )
                for item in catalog.groups[self.group]
            ],
        )
        item_select.callback = self.pick_item
        container.add_item(discord.ui.ActionRow(item_select))
        container.add_item(discord.ui.ActionRow(self._button("Back", self.back_callback)))

    async def open_picker(self, kind: ItemLiteral, interaction: discord.Interaction[discord.Client]) -> None:
        self.kind = kind
        self.group = next(iter(CATALOGS[kind].groups))
        self.show_picker()
        await interaction.response.edit_message(view=self)

    async def pick_group(self, group: str, interaction: discord.Interaction[discord.Client]) -> None:
        self.group = group
        self.show_picker()
        await interaction.response.edit_message(view=self)

    async def back_callback(self, interaction: discord.Interaction[discord.Client]) -> None:
        self.show_overview()
        await interaction.response.edit_message(view=self)

    async def pick_item(self, interaction: discord.Interaction[discord.Client]) -> None:
        catalog = CATALOGS[self.kind]
        key = catalog.enum(selected_value(interaction))

        modal = catalog.modal(key, partial(self.apply_config, self.kind))  # pyright: ignore[reportCallIssue]
        if modal is None:
            await self.apply_config(self.kind, interaction, key, catalog.empty)
            return

        await interaction.response.send_modal(modal)

    if TYPE_CHECKING:

        @overload
        async def apply_config(
            self,
            kind: Literal["trigger"],
            interaction: discord.Interaction[discord.Client],
            type: TriggerType,
            config: TriggerConfig,
        ) -> None: ...

        @overload
        async def apply_config(
            self,
            kind: Literal["condition"],
            interaction: discord.Interaction[discord.Client],
            type: ConditionType,
            config: ConditionConfig,
        ) -> None: ...

        @overload
        async def apply_config(
            self,
            kind: Literal["effect"],
            interaction: discord.Interaction[discord.Client],
            type: EffectType,
            config: EffectConfig,
        ) -> None: ...

    async def apply_config(
        self,
        kind: ItemLiteral,
        interaction: discord.Interaction[discord.Client],
        type,  # noqa: A002
        config,
    ) -> None:
        match kind:
            case "trigger":
                self.trigger = Trigger(type=type, config=config)
            case "condition":
                self.conditions = merge(
                    self.conditions,
                    Condition(type=type, config=config),
                    repeatable=set(),
                    conflicts=CONDITION_CONFLICTS,
                )
            case "effect":
                merged = merge(
                    self.effects,
                    Effect(type=type, config=config),
                    repeatable=REPEATABLE_EFFECTS,
                    conflicts=EFFECT_CONFLICTS,
                )
                if len(merged) > MAX_EFFECTS:
                    await interaction.response.send_message(
                        f"A rule can have at most {MAX_EFFECTS} effects. Remove one first.",
                        ephemeral=True,
                    )
                    return
                self.effects = merged

        self.show_overview()
        await interaction.response.edit_message(view=self)

    async def remove_item(self, kind: Literal["condition", "effect"], interaction: discord.Interaction[discord.Client]) -> None:
        items = self._items(kind)
        index = int(selected_value(interaction))
        if 0 <= index < len(items):
            items.pop(index)

        self.show_overview()
        await interaction.response.edit_message(view=self)

    async def settings_callback(self, interaction: discord.Interaction[discord.Client]) -> None:
        await interaction.response.send_modal(SettingsModal(self))

    async def save_callback(self, interaction: discord.Interaction[discord.Client]) -> None:
        assert self.trigger is not None
        rule = Rule(
            name=self.rule_name,
            trigger=self.trigger,
            conditions=list(self.conditions),
            effects=list(self.effects),
            enabled=self.enabled,
            priority=self.priority,
        )
        await self.save_handler(interaction, rule)
        self.stop()

    async def cancel_callback(self, interaction: discord.Interaction[discord.Client]) -> None:
        await self.cancel_handler(interaction)
        self.stop()
