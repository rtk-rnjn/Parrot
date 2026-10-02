from __future__ import annotations

import itertools
import os
from pathlib import Path

import arrow
import discord
import pygit2
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

__all__ = ("Help",)

BOT_OWNER_ID = os.environ["OWNER_ID"]
COMMANDS_PER_PAGE = 10

BASIC_USAGE = """
1. <foo> - This argument is mandatory
2. <foos...> - This argument is mandatory and can take multiple values
3. [foo] - This argument is optional
4. [foos...] - This argument is optional and can take multiple values
5. [foo=bar] - This argument is optional and has a default value of `bar`
6. [foo|bar] - This argument is optional so you can either use foo or bar, or don't specify it at all

Additionally, the bot uses converters which makes specifying roles, members, channels etc, easy and fool-proof. When asked to specify a member, you can provide it a mention, an id, a name or a nickname. This principle works for every single command where applicable.

> Note: Do not literally type out `<` `>` `[` `]` `|` etc.
"""


class HelpView(discord.ui.LayoutView):
    def __init__(
        self,
        help_command: Help,
        mapping: dict[commands.Cog | None, list[commands.Command]],
        command: commands.Command | None = None,
        hide_back_button: bool = False,
    ) -> None:
        super().__init__(timeout=180)
        self.help_command = help_command
        self.ctx = help_command.context
        self.mapping = mapping
        self.selected_category: str | None = None
        self.page = 0
        self.command = command
        self.hide_back_button = hide_back_button
        self.refresh()

    @property
    def prefix(self) -> str:
        return self.ctx.clean_prefix

    @property
    def categories(self) -> list[tuple[commands.Cog, list[commands.Command]]]:
        return [
            (
                cog,
                sorted((command for command in commands_list if not command.hidden), key=lambda command: command.qualified_name.lower()),
            )
            for cog, commands_list in self.mapping.items()
            if any(not command.hidden for command in commands_list) and cog is not None
        ]

    @property
    def selected_commands(self) -> list[commands.Command]:
        if self.selected_category == "__all__":
            return sorted(
                (command for commands_list in self.mapping.values() for command in commands_list if not command.hidden),
                key=lambda command: command.qualified_name.lower(),
            )
        return next((commands_list for cog, commands_list in self.categories if cog.qualified_name == self.selected_category), [])

    @property
    def page_count(self) -> int:
        return max(1, (len(self.selected_commands) + COMMANDS_PER_PAGE - 1) // COMMANDS_PER_PAGE)

    @property
    def page_commands(self) -> list[commands.Command]:
        start = self.page * COMMANDS_PER_PAGE
        return self.selected_commands[start : start + COMMANDS_PER_PAGE]

    def command_count(self, command: commands.Command) -> int:
        if not isinstance(command, commands.Group):
            return 1
        return 1 + sum(self.command_count(child) for child in command.commands if not child.hidden)

    def refresh(self) -> None:
        self.clear_items()
        if self.command is None:
            self.build_index()
        else:
            self.build_command()

    def build_index(self) -> None:
        previous = discord.ui.Button(
            label="Previous",
            emoji="◀️",
            style=discord.ButtonStyle.secondary,
            disabled=self.selected_category is None or self.page <= 0,
        )
        next_button = discord.ui.Button(
            label="Next",
            emoji="▶️",
            style=discord.ButtonStyle.secondary,
            disabled=self.selected_category is None or self.page >= self.page_count - 1,
        )
        home = discord.ui.Button(
            label="Home",
            emoji="🏠",
            style=discord.ButtonStyle.primary,
            disabled=self.selected_category is None,
        )

        async def previous_callback(interaction: discord.Interaction) -> None:
            self.page -= 1
            self.refresh()
            await interaction.response.edit_message(content=None, embeds=[], attachments=[], view=self)

        async def next_callback(interaction: discord.Interaction) -> None:
            self.page += 1
            self.refresh()
            await interaction.response.edit_message(content=None, embeds=[], attachments=[], view=self)

        async def home_callback(interaction: discord.Interaction) -> None:
            self.selected_category = None
            self.page = 0
            self.command = None
            self.refresh()
            await interaction.response.edit_message(content=None, embeds=[], attachments=[], view=self)

        previous.callback = previous_callback
        next_button.callback = next_callback
        home.callback = home_callback

        categories = self.categories
        container = discord.ui.Container(accent_colour=discord.Colour.blurple())
        bot = self.ctx.bot

        container.add_item(
            discord.ui.TextDisplay(f"## {bot.user.name} Help\nUse `{self.prefix}help <command>` for detailed information about a command.")
        )

        options = [
            discord.SelectOption(
                label=cog.qualified_name[:100],
                value=cog.qualified_name,
                description=(cog.description or "No description provided.")[:100],
                default=cog.qualified_name == self.selected_category,
            )
            for cog, commands_list in categories[:25]
        ]

        if options:
            select = discord.ui.Select(placeholder="Select a category...", options=options)

            async def select_callback(interaction: discord.Interaction) -> None:
                self.selected_category = select.values[0]
                self.page = 0
                self.command = None
                self.refresh()
                await interaction.response.edit_message(content=None, embeds=[], attachments=[], view=self)

            select.callback = select_callback
            container.add_item(discord.ui.ActionRow(select))

        if self.selected_category is None:
            total_commands = sum(self.command_count(command) for _, commands_list in categories for command in commands_list)
            uptime = getattr(bot, "started_at", None)
            creator = f"<@{BOT_OWNER_ID}>"
            commit = self.help_command.get_last_commits()

            info = f"### Bot Information\n**Creator:** {creator} ({BOT_OWNER_ID})\n**Commands:** `{total_commands}`\n"

            if uptime is not None:
                info += f"\n**Uptime:** {discord.utils.format_dt(uptime, 'R')}"

            if commit:
                info += f"\n**Recent Commit:**\n{commit}"

            container.add_item(discord.ui.TextDisplay(info))

            usage = BASIC_USAGE.strip()
            container.add_item(discord.ui.TextDisplay(f"### How to Use\n{usage}"))

            paginator = commands.Paginator(prefix="", suffix="", max_size=3900)

            if paginator.pages:
                container.add_item(discord.ui.TextDisplay(paginator.pages[0]))
        else:
            paginator = commands.Paginator(prefix="", suffix="", max_size=3900)
            paginator.add_line(f"### {self.selected_category}")

            for command in self.page_commands:
                description = command.short_doc or "No description provided."
                paginator.add_line(f"`{self.prefix}{command.qualified_name}` — {description}")

            page = paginator.pages[0] if paginator.pages else "No commands available."
            container.add_item(discord.ui.TextDisplay(page))

            command_options = [
                discord.SelectOption(
                    label=command.qualified_name[:100],
                    value=str(index),
                    description=(command.short_doc or "No description provided.")[:100],
                )
                for index, command in enumerate(self.page_commands)
            ]

            if command_options:
                command_select = discord.ui.Select(placeholder="Select a command...", options=command_options)

                async def command_callback(interaction: discord.Interaction) -> None:
                    self.command = self.page_commands[int(command_select.values[0])]
                    self.refresh()
                    await interaction.response.edit_message(content=None, embeds=[], attachments=[], view=self)

                command_select.callback = command_callback
                container.add_item(discord.ui.ActionRow(command_select))

                container.add_item(discord.ui.ActionRow(previous, next_button, home))

        if self.selected_category is not None:
            container.add_item(discord.ui.TextDisplay(f"*Page {self.page + 1}/{self.page_count} · {len(self.selected_commands)} commands*"))

        self.add_item(container)

    def build_command(self) -> None:
        command = self.command
        if command is None:
            return

        container = discord.ui.Container(accent_colour=discord.Colour.blurple())
        description = command.help or command.short_doc or "No description provided."
        text = (
            f"## `{self.prefix}{command.qualified_name}`\n{description}\n### Usage\n```text\n{self.help_command.get_command_signature(command)}\n```"
        )

        if command.aliases:
            text += f"\n### Aliases\n{', '.join(f'`{self.prefix}{alias}`' for alias in command.aliases)}"

        examples = command.extras.get("examples")
        if isinstance(examples, (list, tuple)) and examples:
            text += f"\n### Examples\n{chr(10).join(f'`{self.prefix}{example}`' for example in examples)}"

        if isinstance(command, commands.Group):
            subcommands = sorted((child for child in command.commands if not child.hidden), key=lambda child: child.name.lower())
            if subcommands:
                text += (
                    f"\n### Subcommands\n{chr(10).join(f'`{child.name}` — {child.short_doc or "No description provided."}' for child in subcommands)}"
                )

        paginator = commands.Paginator(prefix="", suffix="", max_size=3900)
        for line in text.splitlines():
            paginator.add_line(line)

        for page in paginator.pages:
            container.add_item(discord.ui.TextDisplay(page))

        usage_demo = command.extras.get("usage_demo")
        if isinstance(usage_demo, str) and usage_demo:
            container.add_item(
                discord.ui.MediaGallery(discord.MediaGalleryItem(usage_demo, description=f"{command.qualified_name} usage demonstration"))
            )

        back = discord.ui.Button(label="Back", emoji="◀️", style=discord.ButtonStyle.secondary)

        async def back_callback(interaction: discord.Interaction) -> None:
            self.command = None
            self.refresh()
            await interaction.response.edit_message(content=None, embeds=[], attachments=[], view=self)

        back.callback = back_callback
        if not self.hide_back_button:
            container.add_item(discord.ui.ActionRow(back))
        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("This help menu belongs to the user who invoked it.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.walk_children():
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True


class Help(commands.HelpCommand):
    def __init__(self) -> None:
        super().__init__(
            command_attrs={
                "help": "Shows the bot's interactive help menu.",
                "description": "Shows the bot's interactive help menu.",
                "aliases": ["h", "welp", "commands"],
                "hidden": True,
            }
        )

    def format_commit(self, commit: pygit2.Commit) -> str:
        short, _, _ = commit.message.partition("\n")
        short_sha = str(commit.id)[:6]
        commit_time = arrow.Arrow.fromtimestamp(commit.commit_time)
        short = short[:50] + "..." if len(short) > 50 else short
        return f"[`{short_sha}`](https://github.com/rtk-rnjn/Parrot/commit/{commit.id}) {short} ({discord.utils.format_dt(commit_time, 'R')})"

    def get_last_commits(self, count: int = 3) -> str | None:
        if not Path(".git").is_dir():
            return None
        repo = pygit2.Repository(".git")
        return "\n".join(self.format_commit(commit) for commit in itertools.islice(repo.walk(repo.head.target), count)) or None

    def get_command_signature(self, command: commands.Command) -> str:
        return f"{self.clean_prefix}{command.qualified_name} {command.signature}".strip()

    async def send_bot_help(self, mapping: dict[commands.Cog | None, list[commands.Command]]) -> None:
        filtered = {cog: await self.filter_commands(commands_list, sort=True) for cog, commands_list in mapping.items()}
        filtered = {cog: commands_list for cog, commands_list in filtered.items() if commands_list}
        await self.context.reply(view=HelpView(self, filtered))

    async def send_command_help(self, command: commands.Command) -> None:
        await self.context.reply(view=HelpView(self, {command.cog: [command]}, command, hide_back_button=True))

    async def send_group_help(self, group: commands.Group) -> None:
        commands_list = await self.filter_commands(group.commands, sort=True)
        view = HelpView(self, {group.cog: commands_list})
        view.selected_category = group.cog.qualified_name if group.cog else None
        view.refresh()
        await self.context.reply(view=view)

    async def send_cog_help(self, cog: commands.Cog) -> None:
        commands_list = await self.filter_commands(cog.get_commands(), sort=True)
        view = HelpView(self, {cog: commands_list})
        view.selected_category = cog.qualified_name
        view.refresh()
        await self.context.reply(view=view)

    async def send_error(self, error: str) -> None:
        view = discord.ui.LayoutView()
        view.add_item(discord.ui.Container(discord.ui.TextDisplay(f"## Help\n{error}"), accent_colour=discord.Colour.red()))
        await self.context.reply(view=view)

    @property
    def clean_prefix(self) -> str:
        return self.context.clean_prefix if self.context else ""
