from __future__ import annotations

import asyncio
import difflib
import inspect
import itertools
import os
import re
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import arrow
import discord
import pygit2
from discord.ext import commands
from dotenv import load_dotenv

from .utils import BaseLayoutView, NoticeLayout, human_join, truncate

if TYPE_CHECKING:
    from core import Bot

    from .utils.database.models import CommandConfig

load_dotenv()

__all__ = ("Help",)

BOT_OWNER_ID = os.environ["OWNER_ID"]

REPO_SLUG = os.getenv("GITHUB_REPO", "rtk-rnjn/Parrot").removeprefix("https://github.com/").strip("/")
REPO_URL = f"https://github.com/{REPO_SLUG}"

COMMANDS_PER_PAGE = 8
SELECT_LIMIT = 25
COMMIT_COUNT = 3
COMMIT_SUMMARY_LIMIT = 50
SUGGESTION_COUNT = 3
MAX_TEXT = 3800

DEFAULT_EMOJI = "\N{PACKAGE}"
DOT = " \N{MIDDLE DOT} "

PROTECTED_COMMANDS = frozenset({"help"})

CONFIG_ROWS_PER_PAGE = 12
RULE_KEYS = ("allowed_roles", "ignored_roles", "allowed_channels", "ignored_channels")
RULE_LABELS = {
    "ignored_channels": ("Ignored channels", "<#{}>"),
    "ignored_roles": ("Ignored roles", "<@&{}>"),
    "allowed_channels": ("Allowed channels only", "<#{}>"),
    "allowed_roles": ("Allowed roles only", "<@&{}>"),
}

USAGE_LEGEND = (
    "1. `<argument>` required"
    "\n"
    "2. `[argument]` optional"
    "\n"
    "3. `[argument=value]` optional with a default"
    "\n"
    "4. `[arguments...]` several allowed\n"
    "-# Members, roles and channels can be given as a mention, a name or an ID. Do not type the brackets."
)

PERMISSION_NAMES = {
    "administrator": "Administrator",
    "manage_guild": "Manage Server",
    "moderate_members": "Timeout Members",
    "manage_emojis_and_stickers": "Manage Expressions",
    "external_emojis": "Use External Emoji",
    "use_external_emojis": "Use External Emoji",
    "mention_everyone": "Mention @everyone",
    "send_tts_messages": "Send TTS Messages",
    "use_application_commands": "Use Application Commands",
    "view_audit_log": "View Audit Log",
}

BUCKET_NAMES = {
    commands.BucketType.default: "for everyone",
    commands.BucketType.user: "per user",
    commands.BucketType.guild: "per server",
    commands.BucketType.channel: "per channel",
    commands.BucketType.member: "per member",
    commands.BucketType.category: "per category",
    commands.BucketType.role: "per role",
}


@dataclass(slots=True)
class Category:
    """A help menu entry: one or more cogs that share a ``help_category`` name."""

    name: str
    emoji: str
    description: str
    commands: list[commands.Command] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(count_commands(command) for command in self.commands)


def walk_commands(command: commands.Command):
    """Yield ``command`` and every nested subcommand, hidden ones included."""
    yield command
    if isinstance(command, commands.Group):
        for child in sorted(command.commands, key=lambda child: child.name):
            yield from walk_commands(child)


def collect_paths(targets: list[commands.Command]) -> list[str]:
    """Full qualified names (never aliases) for every target and all of its descendants."""
    paths: dict[str, None] = {}
    for root in targets:
        for command in walk_commands(root):
            if command.qualified_name.split()[0] in PROTECTED_COMMANDS:
                continue
            paths[command.qualified_name] = None
    return list(paths)


def count_commands(command: commands.Command, *, include_hidden: bool = False) -> int:
    if not isinstance(command, commands.Group):
        return 1
    return 1 + sum(count_commands(child, include_hidden=include_hidden) for child in command.commands if include_hidden or not child.hidden)


def category_name(cog: commands.Cog) -> str:
    return getattr(cog, "help_category", None) or cog.qualified_name


def build_categories(mapping: dict[commands.Cog | None, list[commands.Command]]) -> list[Category]:
    grouped: dict[str, Category] = {}
    for cog, cog_commands in mapping.items():
        if cog is None or not cog_commands:
            continue

        name = category_name(cog)
        description = getattr(cog, "help_description", None) or cog.description or ""
        category = grouped.get(name)
        if category is None:
            grouped[name] = Category(name, getattr(cog, "help_emoji", DEFAULT_EMOJI), description, list(cog_commands))
            continue

        category.commands.extend(cog_commands)
        if cog.qualified_name == name:
            category.emoji = getattr(cog, "help_emoji", category.emoji)
            category.description = description or category.description

    for category in grouped.values():
        category.commands.sort(key=lambda command: command.qualified_name)
    return sorted(grouped.values(), key=lambda category: category.name.lower())


def permission_label(flag: str) -> str:
    return PERMISSION_NAMES.get(flag, flag.replace("_", " ").title())


def permission_list(perms: dict[str, bool]) -> str:
    return human_join([f"**{permission_label(flag)}**" for flag, wanted in perms.items() if wanted], final="and")


FIXED_CHECKS = {
    "is_owner": "Bot owner only",
    "guild_only": "Servers only",
    "dm_only": "Direct messages only",
    "is_nsfw": "NSFW channels only",
}
PERMISSION_CHECKS = {
    "has_permissions": "You need",
    "has_guild_permissions": "You need",
    "bot_has_permissions": "Bot needs",
    "bot_has_guild_permissions": "Bot needs",
}


def permission_requirement(check: Any) -> tuple[str, list[str]] | None:
    """For a permission check, return ``(subject, [labels])``; ``None`` for any other check."""
    kind = getattr(check, "__qualname__", "").partition(".")[0]
    subject = PERMISSION_CHECKS.get(kind)
    if subject is None:
        return None

    try:
        closure = inspect.getclosurevars(check).nonlocals
    except TypeError, ValueError:
        return None

    perms = closure.get("perms") or {}
    return subject, [permission_label(flag) for flag, wanted in perms.items() if wanted]


def describe_check(check: Any) -> str | None:
    """Turn a non-permission built-in check into a sentence, or ``None`` if unknown."""
    kind = getattr(check, "__qualname__", "").partition(".")[0]
    if kind in FIXED_CHECKS:
        return FIXED_CHECKS[kind]

    try:
        closure = inspect.getclosurevars(check).nonlocals
    except TypeError, ValueError:
        return None

    if kind == "has_role":
        return f"You need the **{closure.get('item')}** role"
    if kind == "has_any_role":
        return f"You need one of these roles: {human_join([f'**{item}**' for item in closure.get('items', ())])}"
    return None


def bucket_name(kind: object) -> str:
    return BUCKET_NAMES.get(kind, "") if isinstance(kind, commands.BucketType) else ""


def describe_cooldown(command: commands.Command) -> str | None:
    cooldown = command._buckets._cooldown
    if cooldown is None:
        return None
    uses = "once" if cooldown.rate == 1 else f"{cooldown.rate} times"
    return f"Usable {uses} every {cooldown.per:g} seconds {bucket_name(command._buckets.type)}".rstrip()


def describe_concurrency(command: commands.Command) -> str | None:
    limit = command._max_concurrency
    if limit is None:
        return None
    return f"Only {limit.number} at a time {bucket_name(limit.per)}".rstrip()


def requirements(command: commands.Command) -> list[str]:
    """Permissions, cooldowns and other limits, including those inherited from parent groups."""
    lines: list[str] = []
    permissions: dict[str, set[str]] = {}  # "You need" / "Bot needs" -> merged permission labels

    node: commands.Command | None = command
    while node is not None:
        for check in node.checks:
            found = permission_requirement(check)
            if found is not None:
                subject, labels = found
                permissions.setdefault(subject, set()).update(labels)
            elif (text := describe_check(check)) and text not in lines:
                lines.append(text)
        node = node.parent  # type: ignore[assignment]

    for subject, labels in permissions.items():
        if labels:
            lines.insert(0, f"{subject} {human_join([f'**{label}**' for label in sorted(labels)], final='and')}")

    lines.extend(text for text in (describe_cooldown(command), describe_concurrency(command)) if text)
    return lines


def argument_lines(command: commands.Command) -> list[str]:
    lines: list[str] = []
    for name, parameter in command.clean_params.items():
        label = f"`{parameter.displayed_name or name}`"
        if parameter.required:
            status = "required"
        elif parameter.displayed_default:
            status = f"optional, defaults to `{parameter.displayed_default}`"
        else:
            status = "optional"
        description = parameter.description
        lines.append(f"{label} - {description} ({status})" if description else f"{label} ({status})")
    return lines


def is_hidden(command: commands.Command) -> bool:
    node: commands.Command | None = command
    while node is not None and False is False:  # noqa: PLR0133
        if node.hidden:
            return True
        node = node.parent  # type: ignore[assignment]
    return False


def source_search_url(query: str) -> str:
    return "https://github.com/search?type=code&q=" + urllib.parse.quote_plus(f"repo:{REPO_SLUG} {query}")


def subcommands_of(command: commands.Command, *, include_hidden: bool = False) -> list[commands.Command]:
    if not isinstance(command, commands.Group):
        return []
    return sorted((child for child in command.commands if include_hidden or not child.hidden), key=lambda child: child.name)


class BulkToggleModal(discord.ui.Modal):
    """Enable or disable several commands or whole categories by typing their names."""

    def __init__(self, help_view: HelpView, enabled: bool) -> None:
        super().__init__(title=f"{'Enable' if enabled else 'Disable'} commands", timeout=300)
        self.help_view = help_view
        self.enabled = enabled
        self.names = discord.ui.TextInput(
            label="Commands or categories",
            style=discord.TextStyle.paragraph,
            placeholder="One per line or comma separated, e.g.\nrandom\nmod ban",
            max_length=1000,
        )
        self.add_item(self.names)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        view = self.help_view
        targets: list[commands.Command] = []
        unknown: list[str] = []

        for raw in re.split(r"[,\n]+", self.names.value):
            name = raw.strip().removeprefix(view.prefix).strip()
            if not name:
                continue
            command = view.ctx.bot.get_command(name)
            if command is not None:
                targets.append(command)  # aliases resolve here; only qualified_name is stored
            elif category := next((c for c in view.categories if c.name.casefold() == name.casefold()), None):
                targets.extend(category.commands)
            else:
                unknown.append(name)

        note = f"\nNot found: {', '.join(f'`{name}`' for name in unknown)}" if unknown else ""
        await view.apply(interaction, targets, self.enabled, note=note)


def channel_defaults(guild: discord.Guild, ids: list[int]) -> list[discord.SelectDefaultValue]:
    """Pre-selected channels for a modal select; channels that no longer exist are dropped."""
    return [
        discord.SelectDefaultValue(id=item, type=discord.SelectDefaultValueType.channel)
        for item in ids
        if guild.get_channel_or_thread(item) is not None
    ][:25]


def role_defaults(guild: discord.Guild, ids: list[int]) -> list[discord.SelectDefaultValue]:
    """Pre-selected roles for a modal select; roles that no longer exist are dropped."""
    return [discord.SelectDefaultValue(id=item, type=discord.SelectDefaultValueType.role) for item in ids if guild.get_role(item) is not None][:25]


class CommandConfigModal(discord.ui.Modal):
    """Configure one command, a group (with all subcommands) or a whole category in one go."""

    def __init__(self, help_view: HelpView, targets: list[commands.Command], *, name: str, enabled: bool) -> None:
        super().__init__(title=truncate(f"Configure {name}", 45), timeout=300)
        self.help_view = help_view
        self.targets = targets

        guild = help_view.ctx.guild
        assert guild is not None
        # A single command or group is pre-filled with its current rules; a category starts blank.
        current = help_view.configs.get(targets[0].qualified_name, {}) if len(targets) == 1 else {}

        self.status = discord.ui.Select(
            options=[
                discord.SelectOption(label="Enabled", value="enabled", emoji="\N{WHITE HEAVY CHECK MARK}", default=enabled),
                discord.SelectOption(label="Disabled everywhere", value="disabled", emoji="\N{NO ENTRY SIGN}", default=not enabled),
            ]
        )
        self.ignored_channels = discord.ui.ChannelSelect(
            placeholder="No ignored channels",
            min_values=0,
            max_values=25,
            required=False,
            default_values=channel_defaults(guild, current.get("ignored_channels") or []),
        )
        self.ignored_roles = discord.ui.RoleSelect(
            placeholder="No ignored roles",
            min_values=0,
            max_values=25,
            required=False,
            default_values=role_defaults(guild, current.get("ignored_roles") or []),
        )
        self.allowed_channels = discord.ui.ChannelSelect(
            placeholder="Works in every channel",
            min_values=0,
            max_values=25,
            required=False,
            default_values=channel_defaults(guild, current.get("allowed_channels") or []),
        )
        self.allowed_roles = discord.ui.RoleSelect(
            placeholder="Usable by every role",
            min_values=0,
            max_values=25,
            required=False,
            default_values=role_defaults(guild, current.get("allowed_roles") or []),
        )

        self.add_item(discord.ui.Label(text="Status", description="Disabled turns it off in the whole server.", component=self.status))
        self.add_item(discord.ui.Label(text="Ignored channels", description="It does nothing in these channels.", component=self.ignored_channels))
        self.add_item(discord.ui.Label(text="Ignored roles", description="Members with these roles cannot use it.", component=self.ignored_roles))
        self.add_item(
            discord.ui.Label(text="Only in these channels", description="Leave empty to allow every channel.", component=self.allowed_channels)
        )
        self.add_item(discord.ui.Label(text="Only for these roles", description="Leave empty to allow every role.", component=self.allowed_roles))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        rules = {
            "ignored_channels": [channel.id for channel in self.ignored_channels.values],
            "ignored_roles": [role.id for role in self.ignored_roles.values],
            "allowed_channels": [channel.id for channel in self.allowed_channels.values],
            "allowed_roles": [role.id for role in self.allowed_roles.values],
        }
        await self.help_view.apply(interaction, self.targets, self.status.values[0] == "enabled", rules=rules)


class HelpView(BaseLayoutView):
    """The interactive help menu: a home page, one page per category and one per command."""

    def __init__(self, help_command: Help, categories: list[Category], *, include_hidden: bool = False) -> None:
        super().__init__(help_command.context.author, timeout=180)
        self.help_command = help_command
        self.ctx = help_command.context
        self.categories = categories
        self.include_hidden = include_hidden
        self.revealed: Category | None = None
        self.category: Category | None = None
        self.command: commands.Command | None = None
        self.page = 0
        self.command_enabled = True
        self.configuring = False
        self.config_rows: list[CommandConfig] = []
        self.disabled: set[str] = set()
        self.configs: dict[str, dict[str, Any]] = {}
        self.admin_row: discord.ui.ActionRow | None = None

        self.container = discord.ui.Container(accent_colour=discord.Colour.blurple())
        self.add_item(self.container)

    @property
    def prefix(self) -> str:
        return self.ctx.clean_prefix

    def category_for(self, command: commands.Command) -> Category | None:
        root = command.root_parent or command
        if root.cog is None:
            return None
        name = category_name(root.cog)
        if self.revealed is not None and self.revealed.name == name:
            return self.revealed
        return next((category for category in self.categories if category.name == name), None)

    async def show_home(self) -> None:
        self.category = None
        self.command = None
        self.configuring = False
        self.page = 0
        await asyncio.to_thread(self.render)

    async def show_category(self, category: Category, *, page: int = 0) -> None:
        self.category = category
        self.command = None
        self.configuring = False
        self.page = page
        if self.ctx.guild is not None and self.is_admin(self.ctx.author):
            await self.load_config()
        await asyncio.to_thread(self.render)

    async def show_command(self, command: commands.Command) -> None:
        self.category = self.category_for(command)
        self.command = command
        self.configuring = False
        if self.ctx.guild is not None:
            if self.is_admin(self.ctx.author):
                await self.load_config()
                self.command_enabled = command.qualified_name not in self.disabled
            else:
                self.command_enabled = await self.ctx.bot.database.is_command_enabled(guild_id=self.ctx.guild.id, command_path=command.qualified_name)
        await asyncio.to_thread(self.render)

    async def edit(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message(view=self)

    def render(self) -> None:
        self.container.clear_items()
        if self.admin_row is not None:
            self.remove_item(self.admin_row)
            self.admin_row = None

        if self.configuring:
            self.render_config()
        elif self.command is not None:
            self.render_command(self.command)
        elif self.category is not None:
            self.render_category(self.category)
        else:
            self.render_home()

        self.build_admin_row()

    def button(
        self,
        label: str,
        handler: Any,
        *,
        emoji: str | None = None,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
        disabled: bool = False,
    ):
        button = discord.ui.Button(label=label, emoji=emoji, style=style, disabled=disabled)
        button.callback = handler
        return button

    def home_button(self) -> discord.ui.Button:
        async def go_home(interaction: discord.Interaction) -> None:
            await self.show_home()
            await self.edit(interaction)

        return self.button("Home", go_home, emoji="\N{HOUSE BUILDING}", style=discord.ButtonStyle.primary)

    def header(self, lines: str) -> None:
        bot_name = self.ctx.bot.user.name if self.ctx.bot.user is not None else "Bot"
        self.container.add_item(discord.ui.TextDisplay(f"## {bot_name} Help\n-# {lines}"))

    def category_selects(self) -> None:
        for chunk in itertools.batched(self.categories, SELECT_LIMIT, strict=False):
            options = [
                discord.SelectOption(
                    label=category.name[:100],
                    value=category.name,
                    description=truncate(category.description, 100) or None,
                    emoji=category.emoji,
                    default=self.category is not None and category.name == self.category.name,
                )
                for category in chunk
            ]
            placeholder = (
                f"Categories {chunk[0].name[0].upper()}\N{EN DASH}{chunk[-1].name[0].upper()}"
                if len(self.categories) > SELECT_LIMIT
                else "Pick a category"
            )
            select = discord.ui.Select(placeholder=placeholder, options=options)

            async def pick(interaction: discord.Interaction, select: discord.ui.Select = select) -> None:
                chosen = next((category for category in self.categories if category.name == select.values[0]), None)
                if chosen is not None:
                    await self.show_category(chosen)
                await self.edit(interaction)

            select.callback = pick
            self.container.add_item(discord.ui.ActionRow(select))

    def render_home(self) -> None:
        total = sum(category.total for category in self.categories)
        self.header(
            f"`{self.prefix}help <command>` explains a command"
            + DOT
            + f"`{self.prefix}help <category>` lists a category"
            + DOT
            + f"{total} commands in {len(self.categories)} categories"
        )
        self.category_selects()
        self.container.add_item(discord.ui.Separator())

        overview = "\n".join(f"{category.emoji} **{category.name}** - {category.description or 'No description.'}" for category in self.categories)
        self.container.add_item(discord.ui.TextDisplay(truncate(overview, MAX_TEXT // 2)))
        self.container.add_item(discord.ui.Separator())
        self.container.add_item(discord.ui.TextDisplay(f"### Reading usage\n{USAGE_LEGEND}"))

        footer = [f"Made by <@{BOT_OWNER_ID}>"]
        footer.append(f"online since {discord.utils.format_dt(self.ctx.bot.started_at, 'R')}")

        self.container.add_item(discord.ui.TextDisplay("-# " + DOT.join(footer)))
        commits = self.help_command.recent_commits(seperator="\n")
        if commits:
            self.container.add_item(discord.ui.TextDisplay(f"### Recent commits\n{commits}"))

    def render_category(self, category: Category) -> None:
        pages = max(1, -(-len(category.commands) // COMMANDS_PER_PAGE))
        self.page = min(self.page, pages - 1)
        shown = category.commands[self.page * COMMANDS_PER_PAGE : (self.page + 1) * COMMANDS_PER_PAGE]

        self.header(f"`{self.prefix}help <command>` explains a command" + DOT + f"{category.total} commands in this category")
        self.category_selects()
        self.container.add_item(discord.ui.Separator())

        lines = [f"## {category.emoji} {category.name}", f"-# {category.description}" if category.description else ""]
        for command in shown:
            extra = f" (+{count_commands(command, include_hidden=self.include_hidden) - 1})" if isinstance(command, commands.Group) else ""
            lines.append(f"`{self.prefix}{command.qualified_name}`{extra} - {command.short_doc or 'No description.'}")
        self.container.add_item(discord.ui.TextDisplay(truncate("\n".join(line for line in lines if line), MAX_TEXT)))

        options = [
            discord.SelectOption(label=command.qualified_name[:100], value=str(index), description=truncate(command.short_doc, 100) or None)
            for index, command in enumerate(shown)
        ]
        select = discord.ui.Select(placeholder="Pick a command for details", options=options)

        async def pick(interaction: discord.Interaction) -> None:
            await self.show_command(shown[int(select.values[0])])
            await self.edit(interaction)

        select.callback = pick
        self.container.add_item(discord.ui.ActionRow(select))

        async def previous(interaction: discord.Interaction) -> None:
            await self.show_category(category, page=self.page - 1)
            await self.edit(interaction)

        async def following(interaction: discord.Interaction) -> None:
            await self.show_category(category, page=self.page + 1)
            await self.edit(interaction)

        self.container.add_item(
            discord.ui.ActionRow(
                self.button("Previous", previous, emoji="\N{BLACK LEFT-POINTING TRIANGLE}", disabled=self.page == 0),
                self.button(f"Page {self.page + 1} of {pages}", previous, disabled=True),
                self.button("Next", following, emoji="\N{BLACK RIGHT-POINTING TRIANGLE}", disabled=self.page >= pages - 1),
                self.home_button(),
            )
        )

    def command_text(self, command: commands.Command) -> str:
        sections: list[str] = []
        meta = [self.category.name if self.category else "Uncategorised"]
        if isinstance(command, commands.HybridCommand | commands.HybridGroup):
            meta.append(f"also `/{command.qualified_name}`")
        if not self.command_enabled:
            meta.append("\N{NO ENTRY SIGN} disabled in this server")
        sections.append(f"## {self.prefix}{command.qualified_name}\n-# {DOT.join(meta)}")
        sections.append(f"### Usage\n`{self.help_command.get_command_signature(command)}`")

        arguments = argument_lines(command)
        if arguments:
            sections.append("### Arguments\n" + "\n".join(arguments))

        needs = requirements(command)
        sections.append("### Requirements\n" + ("\n".join(f"\N{BULLET} {line}" for line in needs) if needs else "No special permissions."))
        if command.aliases:
            sections.append("### Aliases\n" + ", ".join(f"`{alias}`" for alias in command.aliases))

        examples = command.extras.get("examples")
        if isinstance(examples, list | tuple) and examples:
            sections.append("### Examples\n" + "\n".join(f"`{self.prefix}{example}`" for example in examples))

        children = subcommands_of(command, include_hidden=self.include_hidden)
        if children:
            sections.append("### Subcommands\n" + "\n".join(f"`{child.name}` - {child.short_doc or 'No description.'}" for child in children))

        # The description gets whatever room the structured sections leave.
        reserved = sum(len(section) + 1 for section in sections)
        description = truncate((command.help or command.short_doc or "No description.").strip(), max(200, MAX_TEXT - reserved))
        sections.insert(1, description)
        return "\n".join(sections)

    def render_command(self, command: commands.Command) -> None:
        self.container.add_item(discord.ui.TextDisplay(self.command_text(command)))
        self.container.add_item(discord.ui.Separator())

        children = subcommands_of(command, include_hidden=self.include_hidden)
        if children:
            options = [
                discord.SelectOption(label=child.name[:100], value=str(index), description=truncate(child.short_doc, 100) or None)
                for index, child in enumerate(children[:SELECT_LIMIT])
            ]
            select = discord.ui.Select(placeholder="Open a subcommand", options=options)

            async def pick(interaction: discord.Interaction) -> None:
                await self.show_command(children[int(select.values[0])])
                await self.edit(interaction)

            select.callback = pick
            self.container.add_item(discord.ui.ActionRow(select))

        demo = command.extras.get("usage_demo")
        if isinstance(demo, str) and demo:
            self.container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(demo, description=f"{command.qualified_name} demonstration")))

        async def back(interaction: discord.Interaction) -> None:
            if command.parent is not None:
                await self.show_command(command.parent)  # type: ignore[arg-type]
            elif self.category is not None:
                await self.show_category(self.category)
            else:
                await self.show_home()
            await self.edit(interaction)

        back_label = (
            f"Back to {command.full_parent_name}" if command.parent is not None else f"Back to {self.category.name}" if self.category else "Back"
        )
        self.container.add_item(discord.ui.ActionRow(self.button(back_label, back, emoji="\N{BLACK LEFT-POINTING TRIANGLE}"), self.home_button()))

    def is_admin(self, user: discord.abc.User) -> bool:
        return isinstance(user, discord.Member) and user.guild_permissions.administrator

    async def load_config(self) -> None:
        """Fetch this server's command configs so the (sync) render step can draw them."""
        if self.ctx.guild is None:
            return

        configs = await self.ctx.bot.database.get_guild_command_configs(guild_id=self.ctx.guild.id)
        configs = [config for config in configs if config.get("command_path")]
        self.configs = {config["command_path"]: config for config in configs}
        self.disabled = {config["command_path"] for config in configs if not config.get("enabled", True)}
        self.config_rows = sorted(
            (config for config in configs if not config.get("enabled", True) or any(config.get(key) for key in RULE_KEYS)),
            key=lambda config: config["command_path"],
        )

    async def show_config(self, *, page: int = 0) -> None:
        self.category = None
        self.command = None
        self.configuring = True
        self.page = page
        await self.load_config()
        await asyncio.to_thread(self.render)

    async def apply(
        self,
        interaction: discord.Interaction,
        targets: list[commands.Command],
        enabled: bool,
        *,
        note: str = "",
        rules: dict[str, list[int]] | None = None,
    ) -> None:
        """Enable/disable every target and all of its subcommands, optionally setting channel/role rules."""
        await self.apply_paths(interaction, collect_paths(targets), enabled, note=note, rules=rules)

    async def apply_paths(
        self,
        interaction: discord.Interaction,
        paths: list[str],
        enabled: bool,
        *,
        note: str = "",
        rules: dict[str, list[int]] | None = None,
    ) -> None:
        if interaction.guild is None or not self.is_admin(interaction.user):
            await interaction.response.send_message("Only **Administrators** can do that.", ephemeral=True)
            return

        if not paths:
            await interaction.response.send_message(f"Nothing to change.{note}", ephemeral=True)
            return

        database = self.ctx.bot.database
        await database.edit_commands_config(guild_id=interaction.guild.id, command_paths=paths, enabled=enabled, **(rules or {}))

        await self.load_config()
        if self.command is not None:
            self.command_enabled = self.command.qualified_name not in self.disabled

        await asyncio.to_thread(self.render)
        await interaction.response.edit_message(view=self)

        shown = ", ".join(f"`{path}`" for path in paths[:10]) + (f" and {len(paths) - 10} more" if len(paths) > 10 else "")
        lines = [f"{'Enabled' if enabled else 'Disabled'} **{len(paths)}** command(s): {shown}"]
        for key, (label, template) in RULE_LABELS.items():
            ids = (rules or {}).get(key)
            if ids:
                lines.append(f"{label}: " + " ".join(template.format(item) for item in ids))
        await interaction.followup.send("\n".join(lines) + note, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    def build_admin_row(self) -> None:
        """Admin-only buttons, added to the view itself (outside the container) as a normal top-level row."""
        if self.configuring or self.ctx.guild is None or not self.is_admin(self.ctx.author):
            return

        if self.command is not None:
            targets = [self.command]
            noun = "group" if isinstance(self.command, commands.Group) else "command"
            name = self.command.qualified_name
        elif self.category is not None:
            targets = list(self.category.commands)
            noun = "category"
            name = self.category.name
        else:
            targets, noun, name = [], "", ""

        buttons: list[discord.ui.Button] = []
        paths = collect_paths(targets)
        if paths:
            off = sum(1 for path in paths if path in self.disabled)
            size = f" ({len(paths)})" if noun == "category" else f" (+{len(paths) - 1})" if len(paths) > 1 else ""

            def opener(enabled: bool):
                async def callback(interaction: discord.Interaction) -> None:
                    if not self.is_admin(interaction.user):
                        await interaction.response.send_message("Only **Administrators** can do that.", ephemeral=True)
                        return
                    await interaction.response.send_modal(CommandConfigModal(self, targets, name=name, enabled=enabled))

                return callback

            if off < len(paths):
                buttons.append(self.button(f"Disable {noun}{size}", opener(False), emoji="\N{NO ENTRY SIGN}", style=discord.ButtonStyle.danger))
            if off > 0:
                buttons.append(
                    self.button(f"Enable {noun}{size}", opener(True), emoji="\N{WHITE HEAVY CHECK MARK}", style=discord.ButtonStyle.success)
                )

        async def open_config(interaction: discord.Interaction) -> None:
            if not self.is_admin(interaction.user):
                await interaction.response.send_message("Only **Administrators** can do that.", ephemeral=True)
                return
            await self.show_config()
            await self.edit(interaction)

        buttons.append(self.button("Configure Commands", open_config, emoji="\N{GEAR}", style=discord.ButtonStyle.primary))

        self.admin_row = discord.ui.ActionRow(*buttons)
        self.add_item(self.admin_row)

    def config_table(self, rows: list[CommandConfig]) -> str:
        width = max(7, min(28, max(len(row["command_path"]) for row in rows)))
        lines = [f"{'Command':<{width}}  State  AR IR AC IC"]
        for row in rows:
            state = "on" if row.get("enabled", True) else "OFF"
            counts = " ".join(f"{len(row.get(key) or []):>2}" for key in RULE_KEYS)
            lines.append(f"{truncate(row['command_path'], width):<{width}}  {state:<5}  {counts}")
        return "```\n" + "\n".join(lines) + "\n```"

    def render_config(self) -> None:
        rows = self.config_rows
        pages = max(1, -(-len(rows) // CONFIG_ROWS_PER_PAGE))
        self.page = min(self.page, pages - 1)
        shown = rows[self.page * CONFIG_ROWS_PER_PAGE : (self.page + 1) * CONFIG_ROWS_PER_PAGE]

        total = sum(1 for _ in self.ctx.bot.walk_commands())
        with_rules = sum(1 for row in rows if any(row.get(key) for key in RULE_KEYS))

        self.header("Command configuration" + DOT + "administrators only")
        self.container.add_item(
            discord.ui.TextDisplay(
                "## \N{GEAR} Configure Commands\n"
                f"**{len(self.disabled)}** of {total} commands disabled" + DOT + f"**{with_rules}** with role or channel rules"
            )
        )

        category_lines: list[str] = []
        for category in self.categories:
            paths = collect_paths(category.commands)
            off = sum(1 for path in paths if path in self.disabled)
            if off:
                category_lines.append(f"{category.emoji} **{category.name}** - {off}/{len(paths)} disabled")
        if category_lines:
            self.container.add_item(discord.ui.TextDisplay(truncate("### By category\n" + "\n".join(category_lines), 1200)))

        self.container.add_item(discord.ui.Separator())
        if shown:
            self.container.add_item(
                discord.ui.TextDisplay(
                    "### Configured commands\n"
                    + self.config_table(shown)
                    + "\n-# AR / IR = allowed / ignored roles"
                    + DOT
                    + "AC / IC = allowed / ignored channels"
                )
            )
        else:
            self.container.add_item(discord.ui.TextDisplay("### Configured commands\nEvery command is enabled and has no role or channel rules."))
        self.container.add_item(discord.ui.Separator())

        async def previous(interaction: discord.Interaction) -> None:
            await self.show_config(page=self.page - 1)
            await self.edit(interaction)

        async def following(interaction: discord.Interaction) -> None:
            await self.show_config(page=self.page + 1)
            await self.edit(interaction)

        self.container.add_item(
            discord.ui.ActionRow(
                self.button("Previous", previous, emoji="\N{BLACK LEFT-POINTING TRIANGLE}", disabled=self.page == 0),
                self.button(f"Page {self.page + 1} of {pages}", previous, disabled=True),
                self.button("Next", following, emoji="\N{BLACK RIGHT-POINTING TRIANGLE}", disabled=self.page >= pages - 1),
            )
        )

        async def bulk_disable(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(BulkToggleModal(self, False))

        async def bulk_enable(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(BulkToggleModal(self, True))

        async def enable_everything(interaction: discord.Interaction) -> None:
            await self.apply_paths(interaction, sorted(self.disabled), True)

        self.container.add_item(
            discord.ui.ActionRow(
                self.button("Disable by name", bulk_disable, emoji="\N{NO ENTRY SIGN}", style=discord.ButtonStyle.danger),
                self.button("Enable by name", bulk_enable, emoji="\N{WHITE HEAVY CHECK MARK}", style=discord.ButtonStyle.success),
                self.button("Enable all disabled", enable_everything, disabled=not self.disabled),
                self.home_button(),
            )
        )


class HiddenNoticeView(BaseLayoutView):
    """Tells the invoker that something hidden exists, with a button that reveals its help after all."""

    def __init__(self, help_command: Help, *, body: str, title: str, command: commands.Command | None, cog: commands.Cog | None) -> None:
        super().__init__(help_command.context.author, timeout=180)
        self.help_command = help_command
        self.command = command
        self.cog = cog

        button = discord.ui.Button(label="Show help anyway", style=discord.ButtonStyle.secondary, emoji="\N{EYES}")
        button.callback = self.reveal
        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"### {title}\n{body}"),
                discord.ui.ActionRow(button),
                accent_colour=discord.Colour.blurple(),
            )
        )

    async def reveal(self, interaction: discord.Interaction) -> None:
        """Swap in the full help for the hidden target only; menus and the front page stay visible-only."""
        view = await self.help_command.view(include_hidden=True)
        if self.cog is not None:
            view.revealed = await self.help_command.hidden_category(self.cog)
        if self.command is not None:
            if self.command.cog is not None:
                view.revealed = await self.help_command.hidden_category(self.command.cog)
            await view.show_command(self.command)
        elif view.revealed is not None:
            await view.show_category(view.revealed)
        else:
            await view.show_home()
        view.message = interaction.message
        self.stop()
        await interaction.response.edit_message(view=view)


class Help(commands.HelpCommand):
    context: commands.Context[Bot]

    def __init__(self) -> None:
        super().__init__(
            command_attrs={
                "help": "Browse every command by category, or look one up by name.",
                "aliases": ["h", "commands"],
                "hidden": True,
            }
        )

    def get_command_signature(self, command: commands.Command) -> str:
        return f"{self.context.clean_prefix}{command.qualified_name} {command.signature}".strip()

    def recent_commits(self, seperator: str = ", ") -> str | None:
        if not Path(".git").is_dir():
            return None
        try:
            repo = pygit2.Repository(".git")
            commits = itertools.islice(repo.walk(repo.head.target), COMMIT_COUNT)
            return seperator.join(self.format_commit(commit) for commit in commits) or None
        except pygit2.GitError:
            return None

    @staticmethod
    def format_commit(commit: pygit2.Commit) -> str:
        summary = truncate(commit.message.partition("\n")[0], COMMIT_SUMMARY_LIMIT)
        when = arrow.Arrow.fromtimestamp(commit.commit_time).datetime
        return f"[`{str(commit.id)[:7]}`]({REPO_URL}/commit/{commit.id}) {summary} ({discord.utils.format_dt(when, 'R')})"

    async def categories(self) -> list[Category]:
        mapping = self.get_bot_mapping()
        filtered = {cog: await self.filter_commands(cog_commands, sort=True) for cog, cog_commands in mapping.items()}
        return build_categories(filtered)

    async def hidden_category(self, cog: commands.Cog) -> Category | None:
        """A category for one cog with its hidden commands included, kept out of the menus."""
        previous = self.show_hidden
        self.show_hidden = True
        try:
            cog_commands = await self.filter_commands(cog.get_commands(), sort=True)
        finally:
            self.show_hidden = previous
        categories = build_categories({cog: cog_commands})
        return categories[0] if categories else None

    async def view(self, *, include_hidden: bool = False) -> HelpView:
        """The menus always list visible categories only; ``include_hidden`` only affects subcommand listings."""
        return HelpView(self, await self.categories(), include_hidden=include_hidden)

    async def reply(self, view: HelpView) -> None:
        view.message = await self.context.reply(view=view)

    async def command_callback(self, ctx: commands.Context[Bot], /, *, command: str | None = None) -> None:
        if command is not None:
            view = await self.view()
            wanted = command.casefold()
            category = next((category for category in view.categories if category.name.casefold() == wanted), None)
            if category is not None:
                await view.show_category(category)
                await self.reply(view)
                return
        await super().command_callback(ctx, command=command)

    async def send_bot_help(self, mapping: dict[commands.Cog | None, list[commands.Command]]) -> None:
        view = await self.view()
        await view.show_home()
        await self.reply(view)

    async def send_hidden_notice(self, name: str, *, command: commands.Command | None = None, cog: commands.Cog | None = None) -> None:
        """Hidden commands and categories are acknowledged but not documented, unless the invoker insists."""
        category = cog is not None
        label = f"**{name}**" if category else f"`{self.context.clean_prefix}{name}`"
        body = (
            f"{label} exists, but it is hidden and Bot does not document hidden {'categories' if category else 'commands'}.\n"
            f"The source code is public: [browse the repository]({REPO_URL}) or [search for it]({source_search_url(name)})."
        )
        view = HiddenNoticeView(self, body=body, title="Hidden category" if category else "Hidden command", command=command, cog=cog)
        view.message = await self.context.reply(view=view)

    async def send_cog_help(self, cog: commands.Cog) -> None:
        if not any(not command.hidden for command in cog.get_commands()):
            await self.send_hidden_notice(cog.qualified_name, cog=cog)
            return

        view = await self.view()
        name = category_name(cog)
        category = next((category for category in view.categories if category.name == name), None)
        if category is None:
            await self.send_error_message(f"There is nothing you can use in **{cog.qualified_name}**.")
            return
        await view.show_category(category)
        await self.reply(view)

    async def send_group_help(self, group: commands.Group) -> None:
        await self.send_command_help(group)

    async def send_command_help(self, command: commands.Command) -> None:
        if is_hidden(command):
            await self.send_hidden_notice(command.qualified_name, command=command)
            return

        view = await self.view()
        await view.show_command(command)
        await self.reply(view)

    def suggestions(self, query: str) -> str:
        bot = self.context.bot
        names = [command.qualified_name for command in bot.walk_commands() if not is_hidden(command)]
        names += [category_name(cog) for cog in bot.cogs.values() if any(not command.hidden for command in cog.get_commands())]
        matches = difflib.get_close_matches(query.casefold(), {name.casefold(): name for name in names}, n=SUGGESTION_COUNT)
        if not matches:
            return ""
        lookup = {name.casefold(): name for name in names}
        return "\nDid you mean " + human_join([f"`{self.context.clean_prefix}help {lookup[match]}`" for match in matches]) + "?"

    async def command_not_found(self, string: str) -> str:
        return f"No command or category called **{discord.utils.escape_markdown(string)}**.{self.suggestions(string)}"

    async def subcommand_not_found(self, command: commands.Command, string: str) -> str:
        if isinstance(command, commands.Group) and command.commands:
            return f"**{command.qualified_name}** has no subcommand called **{discord.utils.escape_markdown(string)}**.{self.suggestions(f'{command.qualified_name} {string}')}"
        return f"**{command.qualified_name}** has no subcommands."

    async def send_error_message(self, error: str) -> None:
        await self.context.reply(view=NoticeLayout.error(error, title="Help"))
