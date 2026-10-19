from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

from core.utils import truncate

from .base import DISABLED_TEXT, ENABLED_TEXT, ChannelSelect, Interaction, NoticeLevel, Page, RoleSelect, channel_text, role_text

if TYPE_CHECKING:
    from core.utils.database.models import CommandConfig

__all__ = ("CommandConfigPage",)

# Commands that must never be switched off, otherwise admins could lock themselves out.
PROTECTED_COMMANDS = frozenset({"help", "config"})

ALL = "__all__"  # value of the "Entire category" option
MAX_SELECT = 25
PAGE_SIZE = MAX_SELECT - 1  # one slot goes to the "Entire category" option
MAX_LISTED = 8
WARNING = "\N{WARNING SIGN}\N{VARIATION SELECTOR-16}"
DOT = " \N{MIDDLE DOT} "

CHANNEL_TYPES: tuple[discord.ChannelType, ...] = (
    discord.ChannelType.text,
    discord.ChannelType.news,
    discord.ChannelType.voice,
    discord.ChannelType.stage_voice,
    discord.ChannelType.public_thread,
    discord.ChannelType.private_thread,
    discord.ChannelType.news_thread,
)

# key stored in the database -> (label shown to admins, text shown when the list is empty)
RULES: dict[str, tuple[str, str]] = {
    "ignored_channels": ("Ignored channels", "*None*"),
    "ignored_roles": ("Ignored roles", "*None*"),
    "allowed_channels": ("Only in channels", "*Every channel*"),
    "allowed_roles": ("Only for roles", "*Every role*"),
}


@dataclass(slots=True)
class Section:
    """One selectable category: every cog that shares a ``help_category`` (or the cog name)."""

    name: str
    emoji: str | None
    roots: list[commands.Command] = field(default_factory=list)


def descendants(command: commands.Command) -> Iterator[commands.Command]:
    """``command`` and every nested subcommand, hidden ones included."""
    yield command
    if isinstance(command, commands.Group):
        for child in sorted(command.commands, key=lambda child: child.name):
            yield from descendants(child)


def visible_tree(command: commands.Command) -> Iterator[commands.Command]:
    """Like :func:`descendants` but skips hidden subcommands (used for the pick list)."""
    yield command
    if isinstance(command, commands.Group):
        for child in sorted(command.commands, key=lambda child: child.name):
            if not child.hidden:
                yield from visible_tree(child)


def paths_of(roots: Iterable[commands.Command]) -> list[str]:
    """Full qualified names (never aliases) of every command under ``roots``."""
    paths: dict[str, None] = {}
    for root in roots:
        for command in descendants(root):
            if command.qualified_name.split()[0] in PROTECTED_COMMANDS:
                continue
            paths[command.qualified_name] = None
    return list(paths)


class CommandConfigPage(Page):
    key = "commands"
    label = "Commands"
    emoji = "\N{CONTROL KNOBS}"
    description = "Enable or disable commands, or limit them to certain channels and roles."
    section = None  # commands live in their own collection; reset() is overridden below

    def __init__(self, dashboard) -> None:
        super().__init__(dashboard)
        self.loaded = False
        self.configs: dict[str, CommandConfig] = {}
        self.sections: dict[str, Section] = {}

        self.section_name: str | None = None
        self.command_path: str | None = None  # ``None`` means "the entire category"
        self.cmd_page = 0

        self.listed: list[commands.Command] = []
        self.lookup: dict[str, commands.Command] = {}

    async def prepare(self) -> None:
        rows = await self.db.get_guild_command_configs(guild_id=self.guild.id)
        self.configs = {row["command_path"]: row for row in rows if row.get("command_path")}
        self.loaded = True
        self._rebuild()

    def _rebuild(self) -> None:
        """Recompute everything that depends on the selection (no database access)."""
        grouped: dict[str, Section] = {}
        for cog in self.bot.cogs.values():
            roots = [command for command in cog.get_commands() if not command.hidden and command.name not in PROTECTED_COMMANDS]
            if not roots:
                continue
            name = getattr(cog, "help_category", None) or cog.qualified_name
            section = grouped.setdefault(name, Section(name, getattr(cog, "help_emoji", None)))
            section.roots.extend(roots)
        for section in grouped.values():
            section.roots.sort(key=lambda command: command.qualified_name)
        self.sections = dict(sorted(grouped.items(), key=lambda item: item[0].lower()))

        if self.section_name not in self.sections:
            self.section_name = None

        self.listed = []
        if (section := self.current_section) is not None:
            seen: dict[str, commands.Command] = {}
            for root in section.roots:
                for command in visible_tree(root):
                    seen[command.qualified_name] = command
            self.listed = sorted(seen.values(), key=lambda command: command.qualified_name)
        self.lookup = {command.qualified_name: command for command in self.listed}

        if self.command_path not in self.lookup:
            self.command_path = None
        pages = max(1, -(-len(self.listed) // PAGE_SIZE))
        self.cmd_page = max(0, min(self.cmd_page, pages - 1))

    @property
    def current_section(self) -> Section | None:
        return self.sections.get(self.section_name) if self.section_name else None

    @property
    def disabled_paths(self) -> set[str]:
        return {path for path, row in self.configs.items() if not row.get("enabled", True)}

    def has_rules(self, path: str) -> bool:
        row = self.configs.get(path, {})
        return any(row.get(key) for key in RULES)

    @property
    def scope_commands(self) -> list[commands.Command]:
        section = self.current_section
        if section is None:
            return []
        if self.command_path is not None and (command := self.lookup.get(self.command_path)) is not None:
            return [command]
        return section.roots

    @property
    def scope_paths(self) -> list[str]:
        return paths_of(self.scope_commands)

    def scope_name(self) -> str:
        section = self.current_section
        paths = self.scope_paths
        if section is None:
            return "nothing"
        if self.command_path is None:
            return f"all {len(paths)} commands in **{section.name}**"
        extra = len(paths) - 1
        suffix = f" and {extra} subcommand{'' if extra == 1 else 's'}" if extra else ""
        return f"`{self.command_path}`{suffix}"

    def shared(self, key: str) -> list[int] | None:
        """The rule list every command in scope has in common, or ``None`` if they differ."""
        values = [tuple(sorted(self.configs.get(path, {}).get(key) or ())) for path in self.scope_paths]
        if not values:
            return []
        first = values[0]
        return list(first) if all(value == first for value in values) else None

    def list_text(self, key: str) -> str:
        ids = self.shared(key)
        if ids is None:
            return "*Varies between commands*"
        if not ids:
            return RULES[key][1]
        render = channel_text if key.endswith("channels") else role_text
        shown = ", ".join(render(self.guild, item) for item in ids[:MAX_LISTED])
        hidden = len(ids) - MAX_LISTED
        return f"{shown} and {hidden} more" if hidden > 0 else shown

    @staticmethod
    def state_text(off: int, total: int) -> str:
        if total == 0 or off == 0:
            return ENABLED_TEXT
        if off == total:
            return DISABLED_TEXT
        return f"{WARNING} {off} of {total} disabled"

    def summary(self) -> str:
        if not self.loaded:
            return "Enable, disable or restrict commands per channel and role"
        paths = set(paths_of(root for section in self.sections.values() for root in section.roots))
        off = len(paths & self.disabled_paths)
        rules = sum(1 for path in paths if self.has_rules(path))
        return f"{off} of {len(paths)} commands disabled{DOT}{rules} with channel or role rules"

    def reset_summary(self) -> str:
        return "every command: all commands are enabled again and every channel and role rule is removed"

    async def reset(self) -> None:
        rows = await self.db.get_guild_command_configs(guild_id=self.guild.id)
        paths = [row["command_path"] for row in rows if row.get("command_path")]
        await self.db.edit_commands_config(
            guild_id=self.guild.id,
            command_paths=paths,
            enabled=True,
            ignored_roles=[],
            allowed_roles=[],
            ignored_channels=[],
            allowed_channels=[],
        )
        self.section_name = None
        self.command_path = None
        self.cmd_page = 0

    def build(self) -> list[discord.ui.Item]:
        if not self.sections:
            return [self.text("There are no configurable commands.")]
        if self.current_section is None:
            return self._build_overview()
        return self._build_section()

    def _build_overview(self) -> list[discord.ui.Item]:
        disabled = self.disabled_paths
        all_paths = set(paths_of(root for section in self.sections.values() for root in section.roots))
        off = len(all_paths & disabled)
        rules = sum(1 for path in all_paths if self.has_rules(path))

        lines: list[str] = []
        for section in self.sections.values():
            paths = paths_of(section.roots)
            section_off = sum(1 for path in paths if path in disabled)
            if section_off:
                lines.append(f"{section.emoji or ''} **{section.name}** - {section_off}/{len(paths)} disabled".strip())

        items: list[discord.ui.Item] = [
            self.status([("Disabled commands", f"{off} of {len(all_paths)}"), ("With channel or role rules", str(rules))]),
        ]
        if lines:
            items.append(self.text(truncate("**Disabled by category**\n" + "\n".join(lines), 1500)))
        items.append(self.text("-# Pick a category to enable, disable or restrict its commands."))
        items.append(self.row(self.section_select()))
        items.append(self.row(self.reset_button()))
        return items

    def _build_section(self) -> list[discord.ui.Item]:
        section = self.current_section
        assert section is not None
        paths = self.scope_paths
        disabled = self.disabled_paths
        off = sum(1 for path in paths if path in disabled)

        items: list[discord.ui.Item] = [
            self.status(
                [
                    ("Category", f"{section.emoji or ''} {section.name}".strip()),
                    ("Editing", self.scope_name()),
                    ("Status", self.state_text(off, len(paths))),
                    *((RULES[key][0], self.list_text(key)) for key in RULES),
                ]
            ),
            self.row(self.section_select()),
            self.row(self.command_select()),
        ]

        if self.command_path is None:
            noun, size = "category", ""
        else:
            command = self.lookup.get(self.command_path)
            noun = "group" if isinstance(command, commands.Group) else "command"
            size = f" (+{len(paths) - 1})" if len(paths) > 1 else ""

        buttons: list[discord.ui.Item] = []
        if paths and off < len(paths):
            buttons.append(self.button(f"Disable {noun}{size}", self.disable_scope, style=discord.ButtonStyle.danger, emoji="\N{NO ENTRY SIGN}"))
        if off > 0:
            buttons.append(
                self.button(f"Enable {noun}{size}", self.enable_scope, style=discord.ButtonStyle.success, emoji="\N{WHITE HEAVY CHECK MARK}")
            )
        buttons.append(self.button("Clear rules", self.clear_rules, emoji="\N{BROOM}"))
        buttons.append(self.reset_button())
        items.append(self.row(*buttons))

        pages = max(1, -(-len(self.listed) // PAGE_SIZE))
        if pages > 1:
            items.append(
                self.row(
                    self.button("Previous", self.previous_page, emoji="\N{BLACK LEFT-POINTING TRIANGLE}", disabled=self.cmd_page == 0),
                    self.button(f"Commands {self.cmd_page + 1} of {pages}", self.previous_page, disabled=True),
                    self.button("Next", self.next_page, emoji="\N{BLACK RIGHT-POINTING TRIANGLE}", disabled=self.cmd_page >= pages - 1),
                )
            )

        items.append(discord.ui.Separator())
        items.append(self.row(self.channel_rule_select("ignored_channels", "Ignore these channels\N{HORIZONTAL ELLIPSIS}")))
        items.append(self.row(self.role_rule_select("ignored_roles", "Ignore members with these roles\N{HORIZONTAL ELLIPSIS}")))
        items.append(self.row(self.channel_rule_select("allowed_channels", "Only allow these channels\N{HORIZONTAL ELLIPSIS}")))
        items.append(self.row(self.role_rule_select("allowed_roles", "Only allow these roles\N{HORIZONTAL ELLIPSIS}")))
        return items

    def section_select(self) -> discord.ui.Item:
        disabled = self.disabled_paths
        options: list[discord.SelectOption] = []
        for section in list(self.sections.values())[:MAX_SELECT]:
            paths = paths_of(section.roots)
            off = sum(1 for path in paths if path in disabled)
            options.append(
                discord.SelectOption(
                    label=section.name[:100],
                    value=section.name[:100],
                    description=f"{len(paths)} commands{DOT}{off} disabled",
                    emoji=section.emoji,
                    default=section.name == self.section_name,
                )
            )
        return self.string_select("Pick a category\N{HORIZONTAL ELLIPSIS}", options, self.pick_section)

    def command_select(self) -> discord.ui.Item:
        disabled = self.disabled_paths
        section = self.current_section
        total = len(paths_of(section.roots)) if section is not None else 0
        options = [
            discord.SelectOption(
                label="Entire category",
                value=ALL,
                description=f"{total} commands",
                emoji="\N{PACKAGE}",
                default=self.command_path is None,
            )
        ]
        start = self.cmd_page * PAGE_SIZE
        for command in self.listed[start : start + PAGE_SIZE]:
            path = command.qualified_name
            options.append(
                discord.SelectOption(
                    label=path[:100],
                    value=path[:100],
                    description=truncate(command.short_doc, 100) or None,
                    emoji="\N{NO ENTRY SIGN}" if path in disabled else None,
                    default=path == self.command_path,
                )
            )
        return self.string_select("Or pick one command or group\N{HORIZONTAL ELLIPSIS}", options, self.pick_command)

    def channel_rule_select(self, key: str, placeholder: str) -> discord.ui.Item:
        channels = [channel for item in self.shared(key) or [] if (channel := self.guild.get_channel_or_thread(item)) is not None]
        return ChannelSelect(
            self._channel_handler(key),
            placeholder=placeholder,
            channel_types=list(CHANNEL_TYPES),
            min_values=0,
            max_values=MAX_SELECT,
            default_values=channels[:MAX_SELECT],
        )

    def role_rule_select(self, key: str, placeholder: str) -> discord.ui.Item:
        roles = [role for item in self.shared(key) or [] if (role := self.guild.get_role(item)) is not None]
        return RoleSelect(
            self._role_handler(key),
            placeholder=placeholder,
            min_values=0,
            max_values=MAX_SELECT,
            default_values=roles[:MAX_SELECT],
        )

    def _channel_handler(self, key: str) -> Callable[[Interaction, list[int]], Awaitable[None]]:
        async def handler(interaction: Interaction, channel_ids: list[int]) -> None:
            await self.save_rule(interaction, key, list(channel_ids))

        return handler

    def _role_handler(self, key: str) -> Callable[[Interaction, list[discord.Role]], Awaitable[None]]:
        async def handler(interaction: Interaction, roles: list[discord.Role]) -> None:
            await self.save_rule(interaction, key, [role.id for role in roles])

        return handler

    async def refresh(self, interaction: Interaction) -> None:
        """Re-render after a purely visual change, without touching the database."""
        await self.dashboard.acknowledge(interaction)
        self._rebuild()
        self.dashboard.notice = None
        self.dashboard.pending_reset = False
        self.dashboard.render()
        await self.dashboard.respond(interaction)

    async def pick_section(self, interaction: Interaction, values: list[str]) -> None:
        if values and values[0] in self.sections:
            self.section_name = values[0]
            self.command_path = None
            self.cmd_page = 0
        await self.refresh(interaction)

    async def pick_command(self, interaction: Interaction, values: list[str]) -> None:
        value = values[0] if values else ALL
        self.command_path = None if value == ALL else value
        await self.refresh(interaction)

    async def previous_page(self, interaction: Interaction) -> None:
        self.cmd_page -= 1
        await self.refresh(interaction)

    async def next_page(self, interaction: Interaction) -> None:
        self.cmd_page += 1
        await self.refresh(interaction)

    async def _write(self, interaction: Interaction, notice: str, **fields: Any) -> None:
        paths = self.scope_paths
        if not paths:
            await self.commit(interaction, "Nothing to change here.", level=NoticeLevel.ERROR)
            return
        await self.db.edit_commands_config(guild_id=self.guild.id, command_paths=paths, **fields)
        await self.commit(interaction, notice)

    async def disable_scope(self, interaction: Interaction) -> None:
        await self._write(interaction, f"Disabled {self.scope_name()}.", enabled=False)

    async def enable_scope(self, interaction: Interaction) -> None:
        await self._write(interaction, f"Enabled {self.scope_name()}.", enabled=True)

    async def clear_rules(self, interaction: Interaction) -> None:
        await self._write(
            interaction,
            f"Removed every channel and role rule from {self.scope_name()}.",
            ignored_channels=[],
            ignored_roles=[],
            allowed_channels=[],
            allowed_roles=[],
        )

    async def save_rule(self, interaction: Interaction, key: str, ids: list[int]) -> None:
        label = RULES[key][0]
        if not ids:
            await self._write(interaction, f"{label} cleared for {self.scope_name()}.", **{key: []})
            return
        mention = "<#{}>" if key.endswith("channels") else "<@&{}>"
        listed = " ".join(mention.format(item) for item in ids)
        await self._write(interaction, f"{label} for {self.scope_name()}: {listed}", **{key: ids})
