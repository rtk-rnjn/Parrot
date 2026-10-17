from __future__ import annotations

import math
from functools import partial
from typing import TYPE_CHECKING, Protocol

import discord

from core.utils import BaseLayoutView

from .builder import CATALOGS, ItemLiteral, RuleBuilderView, pretty
from .condition import Condition
from .effect import Effect
from .rule import Rule
from .trigger import Trigger

if TYPE_CHECKING:
    from . import Automod

type RuleItem = Trigger | Condition | Effect


PAGE_SIZE = 5
MAX_TEXT = 3800

escape = discord.utils.escape_markdown


class ButtonCallback(Protocol):
    async def __call__(self, interaction: discord.Interaction[discord.Client]) -> None: ...


def make_button(
    label: str,
    callback: ButtonCallback,
    style: discord.ButtonStyle = discord.ButtonStyle.secondary,
    *,
    disabled: bool = False,
) -> discord.ui.Button:
    button = discord.ui.Button(label=label, style=style, disabled=disabled)
    button.callback = callback
    return button


def notice(text: str, colour: discord.Colour) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView()
    view.add_item(discord.ui.Container(discord.ui.TextDisplay(text), accent_colour=colour))
    return view


async def replace_message(interaction: discord.Interaction[discord.Client], view: BaseLayoutView) -> None:
    assert interaction.message is not None
    view.message = interaction.message
    await interaction.response.edit_message(view=view)


async def name_error(instance: Automod, guild_id: int, original: str | None, name: str) -> str | None:
    if original is not None and name.casefold() == original.casefold():
        return None
    if await instance._get_rule(guild_id, name) is not None:
        return f"A rule named {escape(name)!r} already exists."
    return None


def format_line(kind: ItemLiteral, item: RuleItem, prefix: str) -> str:
    detail = CATALOGS[kind].describe(item.config)
    return f"{prefix} **{pretty(item.type)}**" + (f" - {detail}" if detail else "")


def rule_text(rule: Rule) -> str:
    conditions = "\n".join(format_line("condition", item, "\N{BULLET}") for item in rule.conditions) or "*None*"
    effects = "\n".join(format_line("effect", item, f"{index}.") for index, item in enumerate(rule.effects, 1)) or "*None*"
    text = f"### \N{HIGH VOLTAGE SIGN} Trigger\n{format_line('trigger', rule.trigger, '\N{BULLET}')}\n### \N{DIRECT HIT} Conditions\n{conditions}\n### \N{HAMMER AND WRENCH} Effects\n{effects}"
    return text if len(text) <= MAX_TEXT else text[: MAX_TEXT - 1] + "\N{HORIZONTAL ELLIPSIS}"


class ConfirmDeleteView(BaseLayoutView):
    def __init__(
        self,
        author: discord.Member,
        rule: Rule,
        *,
        on_confirm: ButtonCallback,
        on_cancel: ButtonCallback,
    ) -> None:
        super().__init__(author=author)
        self.author = author
        self.message: discord.Message
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"## Delete {escape(rule.name)}?\nThis permanently removes the rule and can't be undone."),
                discord.ui.Separator(visible=False),
                discord.ui.ActionRow(
                    make_button("Delete", self.confirm_callback, discord.ButtonStyle.danger),
                    make_button("Cancel", self.cancel_callback),
                ),
                accent_colour=discord.Colour.red(),
            )
        )

    async def confirm_callback(self, interaction: discord.Interaction[discord.Client]) -> None:
        await self.on_confirm(interaction)
        self.stop()

    async def cancel_callback(self, interaction: discord.Interaction[discord.Client]) -> None:
        await self.on_cancel(interaction)
        self.stop()


class RuleListView(BaseLayoutView):
    def __init__(
        self,
        author: discord.Member,
        instance: Automod,
        guild_id: int,
        rules: list[Rule],
        *,
        page: int = 0,
    ) -> None:
        super().__init__(author=author)
        self.author = author
        self.message: discord.Message
        self.automod_controller = instance
        self.guild_id = guild_id
        self.rules = rules
        self.page = min(page, self.last_page)
        self.selected: Rule | None = None

        self.container = discord.ui.Container()
        self.show_list()
        self.add_item(self.container)

    @classmethod
    async def create(
        cls,
        author: discord.Member,
        instance: Automod,
        guild_id: int,
        *,
        select: str | None = None,
        page: int = 0,
    ) -> RuleListView:
        rules = sorted(await instance._list_rules(guild_id), key=lambda rule: (-rule.priority, rule.name.casefold()))
        view = cls(author, instance, guild_id, rules, page=page)
        if select is not None:
            match = next((rule for rule in rules if rule.name == select), None)
            if match is not None:
                view.selected = match
                view.show_detail(match)
        return view

    @property
    def last_page(self) -> int:
        return max(0, math.ceil(len(self.rules) / PAGE_SIZE) - 1)

    def show_list(self) -> None:
        container = self.container
        container.clear_items()
        container.accent_colour = discord.Colour.blurple()
        container.add_item(discord.ui.TextDisplay(f"# Automod Rules\n-# {len(self.rules)} rule(s), highest priority first"))

        if not self.rules:
            container.add_item(discord.ui.Separator())
            container.add_item(discord.ui.TextDisplay("No rules yet. Create one with `/automod add`."))
            return

        start = self.page * PAGE_SIZE
        for rule in self.rules[start : start + PAGE_SIZE]:
            icon = "\N{LARGE GREEN CIRCLE}" if rule.enabled else "\N{MEDIUM WHITE CIRCLE}"
            container.add_item(discord.ui.Separator())
            container.add_item(
                discord.ui.Section(
                    discord.ui.TextDisplay(
                        f"{icon} **{escape(rule.name)}**\n"
                        f"-# {pretty(rule.trigger.type)} \N{MIDDLE DOT} {len(rule.conditions)} condition(s) \N{MIDDLE DOT} "
                        f"{len(rule.effects)} effect(s) \N{MIDDLE DOT} Priority {rule.priority}"
                    ),
                    accessory=make_button("View", partial(self.open_rule, rule.name)),
                )
            )

        if self.last_page > 0:
            container.add_item(discord.ui.Separator(visible=False))
            container.add_item(
                discord.ui.ActionRow(
                    make_button("Previous", partial(self.turn_page, -1), disabled=self.page == 0),
                    make_button(f"{self.page + 1}/{self.last_page + 1}", self.turn_page_noop, disabled=True),
                    make_button("Next", partial(self.turn_page, 1), disabled=self.page == self.last_page),
                )
            )

    def show_detail(self, rule: Rule) -> None:
        container = self.container
        container.clear_items()
        container.accent_colour = discord.Colour.green() if rule.enabled else discord.Colour.light_grey()

        state = "Enabled" if rule.enabled else "Disabled"
        container.add_item(discord.ui.TextDisplay(f"# {escape(rule.name)}\n-# {state} \N{MIDDLE DOT} Priority {rule.priority}"))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(rule_text(rule)))
        container.add_item(discord.ui.Separator())
        container.add_item(
            discord.ui.ActionRow(
                make_button("Edit", self.edit_selected, discord.ButtonStyle.primary),
                make_button("Delete", self.delete_selected, discord.ButtonStyle.danger),
                make_button("Back", self.back_to_list),
            )
        )

    async def turn_page_noop(self, interaction: discord.Interaction[discord.Client]) -> None:
        await interaction.response.defer()

    async def turn_page(self, step: int, interaction: discord.Interaction[discord.Client]) -> None:
        self.page = max(0, min(self.page + step, self.last_page))
        self.show_list()
        await interaction.response.edit_message(view=self)

    async def back_to_list(self, interaction: discord.Interaction[discord.Client]) -> None:
        self.selected = None
        self.show_list()
        await interaction.response.edit_message(view=self)

    async def vanished(self, name: str, interaction: discord.Interaction[discord.Client]) -> None:
        self.rules = [rule for rule in self.rules if rule.name != name]
        self.page = min(self.page, self.last_page)
        self.selected = None
        self.show_list()
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"**{escape(name)}** no longer exists.", ephemeral=True)

    async def open_rule(self, name: str, interaction: discord.Interaction[discord.Client]) -> None:
        rule = await self.automod_controller._get_rule(self.guild_id, name)
        if rule is None:
            await self.vanished(name, interaction)
            return

        self.selected = rule
        self.show_detail(rule)
        await interaction.response.edit_message(view=self)

    async def return_to_list(self, select: str | None, interaction: discord.Interaction[discord.Client]) -> None:
        view = await RuleListView.create(self.author, self.automod_controller, self.guild_id, select=select, page=self.page)
        await replace_message(interaction, view)

    async def edit_selected(self, interaction: discord.Interaction[discord.Client]) -> None:
        rule = self.selected
        assert rule is not None

        builder = RuleBuilderView(
            self.author,
            rule.name,
            rule=rule,
            on_save=partial(self.finish_edit, rule.name),
            on_cancel=partial(self.return_to_list, rule.name),
            check_name=partial(name_error, self.automod_controller, self.guild_id, rule.name),
        )
        self.stop()
        await replace_message(interaction, builder)

    async def finish_edit(self, original: str, interaction: discord.Interaction[discord.Client], rule: Rule) -> None:
        await self.automod_controller._edit_rule(self.guild_id, original, rule)
        await self.return_to_list(rule.name, interaction)

    async def delete_selected(self, interaction: discord.Interaction[discord.Client]) -> None:
        rule = self.selected
        assert rule is not None

        confirm = ConfirmDeleteView(
            self.author,
            rule,
            on_confirm=partial(self.finish_delete, rule.name),
            on_cancel=partial(self.return_to_list, rule.name),
        )
        self.stop()
        await replace_message(interaction, confirm)

    async def finish_delete(self, name: str, interaction: discord.Interaction[discord.Client]) -> None:
        await self.automod_controller._delete_rule(self.guild_id, name)
        await self.return_to_list(None, interaction)
        await interaction.followup.send(f"Deleted **{escape(name)}**.", ephemeral=True)
