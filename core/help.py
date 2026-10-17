from __future__ import annotations

import asyncio
import difflib
import inspect
import itertools
import os
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


def describe_check(check: Any) -> str | None:
    """Turn one of discord.py's built-in check predicates into a sentence, or ``None`` if unknown."""
    kind = getattr(check, "__qualname__", "").partition(".")[0]
    if kind in FIXED_CHECKS:
        return FIXED_CHECKS[kind]

    try:
        closure = inspect.getclosurevars(check).nonlocals
    except TypeError, ValueError:
        return None

    if kind in PERMISSION_CHECKS:
        perms = closure.get("perms") or {}
        return f"{PERMISSION_CHECKS[kind]} {permission_list(perms)}" if perms else None
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
    node: commands.Command | None = command
    while node is not None:
        for check in node.checks:
            text = describe_check(check)
            if text and text not in lines:
                lines.append(text)
        node = node.parent  # type: ignore[assignment]

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
    while node is not None:
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
        self.page = 0
        await asyncio.to_thread(self.render)

    async def show_category(self, category: Category, *, page: int = 0) -> None:
        self.category = category
        self.command = None
        self.page = page
        await asyncio.to_thread(self.render)

    async def show_command(self, command: commands.Command) -> None:
        self.category = self.category_for(command)
        self.command = command
        await asyncio.to_thread(self.render)

    async def edit(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message(view=self)

    def render(self) -> None:
        self.container.clear_items()
        if self.command is not None:
            self.render_command(self.command)
        elif self.category is not None:
            self.render_category(self.category)
        else:
            self.render_home()

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
        if (started := getattr(self.ctx.bot, "_started_at", None)) is not None:
            footer.append(f"online since {discord.utils.format_dt(started, 'R')}")

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
        sections.append(f"## {self.prefix}{command.qualified_name}\n-# {DOT.join(meta)}")
        sections.append(f"### Usage\n`{self.help_command.get_command_signature(command)}`")

        if arguments := argument_lines(command):
            sections.append("### Arguments\n" + "\n".join(arguments))
        needs = requirements(command)
        sections.append("### Requirements\n" + ("\n".join(f"\N{BULLET} {line}" for line in needs) if needs else "No special permissions."))
        if command.aliases:
            sections.append("### Aliases\n" + ", ".join(f"`{alias}`" for alias in command.aliases))

        examples = command.extras.get("examples")
        if isinstance(examples, list | tuple) and examples:
            sections.append("### Examples\n" + "\n".join(f"`{self.prefix}{example}`" for example in examples))
        if children := subcommands_of(command, include_hidden=self.include_hidden):
            sections.append("### Subcommands\n" + "\n".join(f"`{child.name}` - {child.short_doc or 'No description.'}" for child in children))

        # The description gets whatever room the structured sections leave.
        reserved = sum(len(section) + 1 for section in sections)
        description = truncate((command.help or command.short_doc or "No description.").strip(), max(200, MAX_TEXT - reserved))
        sections.insert(1, description)
        return "\n".join(sections)

    def render_command(self, command: commands.Command) -> None:
        self.container.add_item(discord.ui.TextDisplay(self.command_text(command)))
        self.container.add_item(discord.ui.Separator())

        if children := subcommands_of(command, include_hidden=self.include_hidden):
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
                self.show_command(command.parent)  # type: ignore[arg-type]
            elif self.category is not None:
                await self.show_category(self.category)
            else:
                await self.show_home()
            await self.edit(interaction)

        back_label = (
            f"Back to {command.full_parent_name}" if command.parent is not None else f"Back to {self.category.name}" if self.category else "Back"
        )
        self.container.add_item(discord.ui.ActionRow(self.button(back_label, back, emoji="\N{BLACK LEFT-POINTING TRIANGLE}"), self.home_button()))


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
