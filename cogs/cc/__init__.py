from __future__ import annotations

import inspect
import logging
import re
import traceback
from enum import Enum
from typing import TYPE_CHECKING, Annotated

import discord
from colorama import Fore
from discord.ext import commands

from core.utils import PaginationView
from core.utils.database_manager.models import CustomCommand as CustomCommandModel

from .jinja import render_sandboxed
from .variables import JinjaChannel, JinjaGuild, JinjaMember, JinjaMessage

if TYPE_CHECKING:
    from core.bot import Parrot

VALID_COMMAND_NAME = re.compile(r"^[a-z0-9_-]{1,32}$", re.IGNORECASE)

_log = logging.getLogger("bot.cogs.cc")


CUSTOM_COMMAND_HELP = r"""
# Custom Commands Overview
The custom command system allows you to create dynamic, personalized commands for your server using the **Jinja2** templating language.

## How it works
When a user triggers a custom command, the bot processes your template and sends the resulting text. You can insert variables (like the user's name), create conditions (`if`/`else`), and manipulate text.

**Basic Syntax:**
- `{{ ... }}` : Prints the result of a variable (e.g., `{{ author.name }}`).
- `{% ... %}` : Executes logic like loops or conditions.

*Note: Templates are strictly sandboxed. Infinite loops, heavy math, and external imports are disabled to keep the bot safe and responsive.*
"""


def format_sandbox_error(error: Exception) -> str:
    """Format a sandbox error for display."""
    tb = traceback.format_exception(type(error), error, error.__traceback__)
    return "".join(tb)


def _split_discord_text(text: str, *, max_chars: int = 1800) -> list[str]:
    """Split a response into Discord-safe chunks while preserving paragraphs."""
    chunks: list[str] = []
    current = ""

    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())
            current = ""

        if len(paragraph) <= max_chars:
            current = paragraph
        else:
            for line in paragraph.splitlines():
                if len(current) + len(line) + 1 <= max_chars:
                    current = f"{current}\n{line}" if current else line
                else:
                    if current:
                        chunks.append(current.strip())
                    current = line

    if current:
        chunks.append(current.strip())

    return [chunk for chunk in chunks if chunk]


def _make_help_embed(title: str, body: str) -> discord.Embed:
    """Build a compact, Discord-friendly embed for custom command help."""
    return discord.Embed(title=title, description=body, color=discord.Color.blurple())


CUSTOM_COMMAND_VARIABLES_PAGES = [
    _make_help_embed(
        "Variables: Author & Message",
        inspect.cleandoc("""
        These objects represent the user who triggered the command and the message they sent.

        **`author` (The User)**
        - `author.name`: Their username (e.g., `user123`)
        - `author.display_name`: Their global display name
        - `author.mention`: Mentions the user (`@user123`)

        **`message` (The Trigger)**
        - `message.content`: The full text of the command message
        - `message.id`: The unique Discord message ID
        """),
    ),
    _make_help_embed(
        "Variables: Guild & Channel",
        inspect.cleandoc("""
        These objects represent the server and the channel where the command was used.

        **`guild` (The Server)**
        - `guild.name`: Server name
        - `guild.member_count`: Total number of members
        - `guild.icon_url`: Link to the server icon

        **`channel` (The Channel)**
        - `channel.name`: Channel name (e.g., `general`)
        - `channel.mention`: Clickable channel link (`#general`)
        - `channel.position`: Channel's position in the list
        """),
    ),
    _make_help_embed(
        "Logic: Conditionals (If/Else)",
        inspect.cleandoc("""
        Make your commands respond differently based on specific conditions.

        **Syntax:**
        ```jinja
        {% if author.name == 'admin' %}
          Hello, boss!
        {% elif guild.member_count > 1000 %}
          We are a huge server!
        {% else %}
          Hello, {{ author.display_name }}!
        {% endif %}
        ```
        *Tip: Always remember to close your blocks with `{% endif %}`!*
        """),
    ),
    _make_help_embed(
        "Logic: Loops (For)",
        inspect.cleandoc("""
        Loops allow you to repeat actions or iterate through lists (like words in a message).

        **Syntax:**
        ```jinja
        Here are the words you typed:
        {% for word in message.content.split() %}
        - {{ word }}
        {% endfor %}
        ```
        *Note: Loops are limited by the sandbox to prevent spam. Keep them short!*
        """),
    ),
]

CUSTOM_COMMAND_EXAMPLES_PAGES = [
    _make_help_embed(
        "Examples: Simple Replies",
        inspect.cleandoc("""
        **Welcome Message**
        ```jinja
        Welcome to {{ guild.name }}, {{ author.mention }}! We now have {{ guild.member_count }} members.
        ```
        **Echo Command**
        ```jinja
        You said: {{ message.content }}
        ```
        **Server Info**
        ```jinja
        Server: {{ guild.name }}
        Icon: {{ guild.icon_url }}
        ```
        """),
    ),
    _make_help_embed(
        "Examples: Smart Conditions",
        inspect.cleandoc("""
        **Keyword Matching**
        ```jinja
        {% if 'help' in message.content.lower() %}
          It looks like you need help! Check out the rules channel.
        {% else %}
          Command received, {{ author.display_name }}.
        {% endif %}
        ```
        **Name-based Responses**
        ```jinja
        {% if author.nick and 'VIP' in author.nick %}
          Access granted for VIP!
        {% else %}
          Standard user access.
        {% endif %}
        ```
        """),
    ),
    _make_help_embed(
        "Examples: Text Manipulation",
        inspect.cleandoc("""
        You can use standard string manipulation methods directly in the template.

        **Uppercase Shout**
        ```jinja
        {{ message.content.upper() }}!!!
        ```
        **Word Counter**
        ```jinja
        Your message has {{ message.content.split()|length }} words!
        ```
        **Character Replacer**
        ```jinja
        {{ message.content.replace('a', '@') }}
        ```
        """),
    ),
    _make_help_embed(
        "Examples: Math & Sandbox Limits",
        inspect.cleandoc("""
        Basic math is supported, but strictly capped to prevent lag.

        **Calculations**
        ```jinja
        Members needed for 1000: {{ 1000 - guild.member_count }}
        ```

        **Sandbox Restrictions applied:**
        - Output length is restricted.
        - String repetition (`'a' * 10000`) is capped.
        - Heavy exponents (`10 ** 100`) will fail.
        - `import` and `include` tags are disabled.
        """),
    ),
    _make_help_embed(
        "Examples: Basic Arithmetic",
        inspect.cleandoc("""
        You can perform basic arithmetic operations in your templates.

        **Addition**
        ```jinja
        The sum is: {{ 5 + 3 }}
        ```
        **Subtraction**
        ```jinja
        The difference is: {{ 10 - 4 }}
        ```
        **Multiplication**
        ```jinja
        The product is: {{ 6 * 7 }}
        ```
        **Division**
        ```jinja
        The quotient is: {{ 20 / 4 }}
        ```
        Note: Don't try to `[None] * 100_000_000` or similar, as the sandbox will prevent it to avoid performance issues.
        """),
    ),
    _make_help_embed(
        "Examples: Advanced Logic",
        inspect.cleandoc("""
        **Nested Conditions**
        ```jinja
        {% if author.name == 'admin' %}
            Welcome, admin!
        {% else %}
            {% if guild.member_count > 1000 %}
                We are a large server!
            {% else %}
                Hello, {{ author.display_name }}!
            {% endif %}
        {% endif %}
        ```
        """),
    ),
    _make_help_embed(
        "Examples: Looping Through Words",
        inspect.cleandoc("""
        **Iterating Over Words**
        ```jinja
        {% for word in message.content.split() %}
            {{ word }}
        {% endfor %}
        ```
        """),
    ),
    _make_help_embed(
        "Examples: Variable assignment and filters",
        inspect.cleandoc("""
        **Variable Assignment**
        ```jinja
        {% set user_name = author.display_name %}
        Hello, {{ user_name }}!
        ```
        **Using Filters**
        ```jinja
        {{ message.content | upper }}
        ```
        **Using Logic Filters**
        ```jinja
        {% if guild.member_count | int > 1000 %}
            We have a large community!
        {% endif %}
        ```
        """),
    ),
]


class CustomCommandModal(discord.ui.Modal):
    """Shared modal fields for custom-command operations."""

    def __init__(  # noqa: PLR0913
        self,
        title: str,
        *,
        include_name_input: bool = True,
        include_response: bool,
        custom_command_name: str | None = None,
        custom_command_response: str | None = None,
        custom_command_ignored_roles: list[int] | None = None,
        custom_command_ignored_channels: list[int] | None = None,
    ) -> None:
        super().__init__(title=title)
        self.custom_command_name = custom_command_name
        self.custom_command_response = custom_command_response
        self.custom_command_ignored_roles = custom_command_ignored_roles or []
        self.custom_command_ignored_channels = custom_command_ignored_channels or []

        self.include_name_input = include_name_input

        if include_name_input:
            self.name_input = discord.ui.TextInput(
                label="Command name",
                placeholder="welcome",
                max_length=32,
                default=custom_command_name,
                required=True,
            )
            self.add_item(self.name_input)

        self.ignored_roles_select = discord.ui.Label(
            text="Ignored Roles",
            description="Commands wont invoke for members with these roles.",
            component=discord.ui.RoleSelect(
                default_values=[discord.Object(id=role_id) for role_id in self.custom_command_ignored_roles],
            ),
        )

        self.ignored_channels_select = discord.ui.Label(
            text="Ignored Channels",
            description="Commands wont invoke in these channels.",
            component=discord.ui.ChannelSelect(
                default_values=[discord.Object(id=channel_id) for channel_id in self.custom_command_ignored_channels],
            ),
        )
        self.add_item(self.ignored_roles_select)
        self.add_item(self.ignored_channels_select)
        self.response_input: discord.ui.TextInput | None = None
        if include_response:
            self.response_input = discord.ui.TextInput(
                label="Response template",
                placeholder="Hello {{ author.display_name }}!",
                style=discord.TextStyle.paragraph,
                max_length=3000,
                default=custom_command_response,
                required=True,
            )
            self.add_item(self.response_input)

    async def send_result(self, interaction: discord.Interaction[Parrot], message: str) -> None:
        await interaction.response.send_message(message, ephemeral=True)


class ModalType(Enum):
    CREATE = "create"
    EDIT = "edit"


class CreateEditCustomCommandModal(CustomCommandModal):
    def __init__(self, modal_type: ModalType, **kw) -> None:
        super().__init__("Create custom command", include_response=True, **kw)
        self.modal_type = modal_type

    def _get_command_name(self) -> str:
        """Extract and normalize command name."""
        if hasattr(self, "name_input"):
            name = str(self.name_input.value).strip().lower()
        elif self.custom_command_name is not None:
            name = str(self.custom_command_name).strip().lower()
        else:
            raise RuntimeError("No command name available")
        return name

    async def _validate_and_execute(self, interaction: discord.Interaction[Parrot], name: str) -> bool:
        """Validate name and execute database operation. Returns True if successful."""
        if not VALID_COMMAND_NAME.match(name):
            await self.send_result(interaction, f"`{name}` is not a valid command name. Use only letters, numbers, underscores, and hyphens.")
            return False

        if interaction.guild_id is None:
            await self.send_result(interaction, "This command can only be used in a guild.")
            return False

        assert isinstance(self.ignored_roles_select.component, discord.ui.RoleSelect)
        assert isinstance(self.ignored_channels_select.component, discord.ui.ChannelSelect)

        ignored_roles = self.ignored_roles_select.component.values
        ignored_channels = self.ignored_channels_select.component.values

        assert self.response_input is not None
        func = (
            interaction.client.database_manager.edit_custom_command
            if self.modal_type == ModalType.EDIT
            else interaction.client.database_manager.add_custom_command
        )

        existing_bot_command = interaction.client.get_command(name.lower().strip())
        if existing_bot_command is not None:
            await self.send_result(
                interaction,
                f"A command with the name `{name}` already exists as a bot command. Please choose a different name.\n"
                + (f"-# Help: {existing_bot_command.help}" if existing_bot_command.help else ""),
            )
            return False
        success = await func(
            guild_id=interaction.guild_id,
            name=name,
            response=self.response_input.value,
            ignored_roles=[role.id for role in ignored_roles],
            ignored_channels=[channel.id for channel in ignored_channels],
        )

        if not success:
            error_msg = (
                f"No command with the name `{name}` exists."
                if self.modal_type == ModalType.EDIT
                else f"A command with the name `{name}` already exists."
            )
            await self.send_result(interaction, error_msg)
            return False

        action = "updated" if self.modal_type == ModalType.EDIT else "created"
        await self.send_result(interaction, f"Custom command `{name}` has been {action}.")
        return True

    async def on_submit(self, interaction: discord.Interaction[Parrot]) -> None:
        name = self._get_command_name()
        await self._validate_and_execute(interaction, name)


class DeleteCustomCommandButton(discord.ui.Button):
    def __init__(self, command_name: str) -> None:
        super().__init__(label="Delete", style=discord.ButtonStyle.red)
        self.command_name = command_name

    async def callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("This command can only be used in a guild.", ephemeral=True)
            return

        deleted = await interaction.client.database_manager.delete_custom_command(guild_id=interaction.guild_id, name=self.command_name)
        message = (
            f"No command with the name `{self.command_name}` exists." if not deleted else f"Custom command `{self.command_name}` has been deleted."
        )
        await interaction.response.send_message(message, ephemeral=True)


class CreateCustomCommandButton(discord.ui.Button):
    def __init__(self, **kw) -> None:
        super().__init__(label="Create", style=discord.ButtonStyle.green, **kw)
        self.kw = kw

    async def callback(self, interaction: discord.Interaction[Parrot]) -> None:
        modal = CreateEditCustomCommandModal(modal_type=ModalType.CREATE, **self.kw)
        await interaction.response.send_modal(modal)


class EditCustomCommandButton(discord.ui.Button):
    def __init__(
        self,
        *,
        command_name: str,
        command_response: str,
        custom_command_ignored_roles: list[int],
        custom_command_ignored_channels: list[int],
        **kw,
    ) -> None:
        super().__init__(label="Edit", style=discord.ButtonStyle.blurple)
        self.command_name = command_name
        self.command_response = command_response
        self.custom_command_ignored_roles = custom_command_ignored_roles
        self.custom_command_ignored_channels = custom_command_ignored_channels

        self.kw = kw

    async def callback(self, interaction: discord.Interaction[Parrot]) -> None:
        modal = CreateEditCustomCommandModal(
            modal_type=ModalType.EDIT,
            include_name_input=False,
            custom_command_name=self.command_name,
            custom_command_response=self.command_response,
            custom_command_ignored_roles=self.custom_command_ignored_roles,
            custom_command_ignored_channels=self.custom_command_ignored_channels,
            **self.kw,
        )
        await interaction.response.send_modal(modal)


class CustomCommandVariablesButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Variables", style=discord.ButtonStyle.gray)

    async def callback(self, interaction: discord.Interaction[Parrot]) -> None:
        view = PaginationView(CUSTOM_COMMAND_VARIABLES_PAGES, author=interaction.user)
        await interaction.response.send_message(embed=CUSTOM_COMMAND_VARIABLES_PAGES[0], view=view, ephemeral=True)


class CustomCommandExamplesButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Examples", style=discord.ButtonStyle.gray)

    async def callback(self, interaction: discord.Interaction[Parrot]) -> None:
        view = PaginationView(CUSTOM_COMMAND_EXAMPLES_PAGES, author=interaction.user)
        await interaction.response.send_message(embed=CUSTOM_COMMAND_EXAMPLES_PAGES[0], view=view, ephemeral=True)


class CustomCommandSelect(discord.ui.Select):
    def __init__(self, custom_commands: list[CustomCommandModel]) -> None:
        self.custom_commands = custom_commands
        options = [
            discord.SelectOption(
                label=command["name"],
                description=command["response"][:80] + ("..." if len(command["response"]) > 80 else ""),
            )
            for command in custom_commands
        ]
        super().__init__(placeholder="Select a command to edit or delete", options=options)

    async def callback(self, interaction: discord.Interaction[Parrot]) -> None:
        selected_command = self.values[0]
        command = next((command for command in self.custom_commands if command["name"] == selected_command), None)

        embed = discord.Embed(title=f"Edit or Delete Custom Command: {selected_command}", description=command["response"] if command else "")
        view = discord.ui.View()
        view.add_item(
            EditCustomCommandButton(
                command_name=selected_command,
                command_response=command["response"] if command else "",
                custom_command_ignored_roles=command["ignored_roles"] if command else [],
                custom_command_ignored_channels=command["ignored_channels"] if command else [],
            ),
        )
        view.add_item(DeleteCustomCommandButton(command_name=selected_command))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CustomCommandLayout(discord.ui.LayoutView):
    def __init__(self, *, custom_commands: list[CustomCommandModel] | None = None, logs: list[str] | None = None):
        super().__init__()
        items = []

        if logs:
            items.append(discord.ui.TextDisplay("## Logs"))
            items.append(discord.ui.TextDisplay("\n".join([f"- {log}" for log in logs[:10]])))
        else:
            items.append(discord.ui.TextDisplay(CUSTOM_COMMAND_HELP.strip()))

        items.append(discord.ui.Separator(visible=False))

        if custom_commands:
            items.append(discord.ui.ActionRow(CustomCommandSelect(custom_commands=custom_commands)))
            items.append(discord.ui.Separator())

        items.append(discord.ui.ActionRow(CreateCustomCommandButton(), CustomCommandVariablesButton(), CustomCommandExamplesButton()))

        container = discord.ui.Container(*items)

        self.add_item(container)


class CustomCommand(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

    @commands.group(name="cc", aliases=["customcommand"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def cc(self, ctx: commands.Context[Parrot]) -> None:
        """Manage custom commands."""
        await self.send_panel(ctx)

    async def _build_and_send_panel(
        self,
        ctx: commands.Context[Parrot],
        *,
        pages: list[str],
        select_menu: CustomCommandSelect | None,
        logs: list[str],
    ) -> None:
        """Build and send the management panel with appropriate pagination."""

        custom_commands = await ctx.bot.database_manager.get_custom_commands(ctx.guild.id) if ctx.guild else []
        logs = await ctx.bot.database_manager.get_custom_command_logs(guild_id=ctx.guild.id) if ctx.guild else []
        layout = CustomCommandLayout(custom_commands=custom_commands, logs=logs)

        await ctx.reply(view=layout)

    async def send_panel(self, ctx: commands.Context[Parrot]) -> None:
        if ctx.guild is None:
            return

        custom_commands = await self.bot.database_manager.get_custom_commands(ctx.guild.id)
        pages = [f"- {command['name']}: {command['response'][:80]}{'...' if len(command['response']) > 80 else ''}" for command in custom_commands]
        select_menu = CustomCommandSelect(custom_commands=custom_commands) if custom_commands else None
        logs = await self.bot.database_manager.get_custom_command_logs(guild_id=ctx.guild.id)

        await self._build_and_send_panel(ctx, pages=pages, select_menu=select_menu, logs=logs)

    @cc.command(name="manage")
    async def manage(self, ctx: commands.Context[Parrot]) -> None:
        """Open the custom-command management panel."""
        await self.send_panel(ctx)

    def prepare_context(self, ctx: commands.Context[Parrot]) -> dict[str, object]:
        """Prepare a context for a custom command."""
        assert ctx.guild is not None and isinstance(ctx.channel, discord.abc.GuildChannel)
        return {
            "channel": JinjaChannel(channel=ctx.channel),
            "guild": JinjaGuild(guild=ctx.guild),
            "author": JinjaMember(member=ctx.author),
            "message": JinjaMessage(message=ctx.message),
        }

    async def _render_custom_command(self, ctx: commands.Context[Parrot], response: str, command_id: str | None = None) -> str | None:
        """Render a custom command response. Returns rendered text or None on error."""
        try:
            return await render_sandboxed(response, **self.prepare_context(ctx))
        except Exception as e:
            error_msg = f"```ansi\n{Fore.BLUE}Error while rendering cc id: {command_id}```\n```ansi\n{Fore.RED}{format_sandbox_error(e)}```"
            await ctx.reply(error_msg)
            return None

    @cc.command(name="test", hidden=True)
    @commands.is_owner()
    async def add_custom_command(self, ctx: commands.Context[Parrot], *, response: str) -> None:
        response = response.strip("`")
        rendered = await self._render_custom_command(ctx, response)
        if rendered:
            await ctx.reply(rendered)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return

        context = await self.bot.get_context(message)
        if context.command is not None or context.invoked_with is None:
            return

        command = await self.bot.database_manager.get_custom_command(guild_id=message.guild.id, name=context.invoked_with)
        if command is None:
            return

        response = command["response"]

        ignored_roles = command.get("ignored_roles", [])
        ignored_channels = command.get("ignored_channels", [])

        assert isinstance(message.author, discord.Member)
        if any(role.id in ignored_roles for role in message.author.roles) or message.channel.id in ignored_channels:
            return

        rendered = await self._render_custom_command(context, response, command_id=context.invoked_with)
        relative_dt = discord.utils.format_dt(message.created_at, style="R")
        if rendered:
            await self.bot.database_manager.push_custom_command_log(
                guild_id=message.guild.id,
                log_entry=f"{relative_dt} User {message.author} (`{message.author.id}`) invoked custom command `{context.invoked_with}` in channel {message.channel} (`{message.channel.id}`).",
            )
            if len(rendered) > 2000:
                rendered = f"{rendered[:1997]}..."
            await message.channel.send(rendered)

    @cc.command(name="edit")
    @commands.has_permissions(administrator=True)
    async def edit_custom_command(
        self,
        ctx: commands.Context[Parrot],
        name: Annotated[str, commands.clean_content] = commands.parameter(description="The name of the custom command to edit."),
    ) -> None:
        """Edit an existing custom command."""
        if ctx.guild is None:
            await ctx.reply("This command can only be used in a guild.")
            return

        command = await self.bot.database_manager.get_custom_command(guild_id=ctx.guild.id, name=name)
        if command is None:
            await ctx.reply(f"No command with the name `{name}` exists.")
            return

        button = EditCustomCommandButton(
            command_name=name,
            command_response=command["response"],
            custom_command_ignored_roles=command["ignored_roles"],
            custom_command_ignored_channels=command["ignored_channels"],
        )
        embed = discord.Embed(title=f"Edit Custom Command: {name}", description=command["response"])
        view = discord.ui.View()
        view.add_item(button)
        await ctx.reply(embed=embed, view=view)

    @cc.command(name="delete")
    @commands.has_permissions(administrator=True)
    async def delete_custom_command(
        self,
        ctx: commands.Context[Parrot],
        name: Annotated[str, commands.clean_content] = commands.parameter(description="The name of the custom command to delete."),
    ) -> None:
        """Delete an existing custom command."""
        if ctx.guild is None:
            await ctx.reply("This command can only be used in a guild.")
            return

        result = await self.bot.database_manager.delete_custom_command(guild_id=ctx.guild.id, name=name)
        if not result:
            await ctx.reply(f"No command with the name `{name}` exists.")
            return

        await ctx.reply(f"Command `{name}` deleted.")

    @cc.command(name="rename")
    @commands.has_permissions(administrator=True)
    async def rename_custom_command(
        self,
        ctx: commands.Context[Parrot],
        old_name: Annotated[str, commands.clean_content] = commands.parameter(description="The current name of the custom command."),
        new_name: Annotated[str, commands.clean_content] = commands.parameter(description="The new name for the custom command."),
    ) -> None:
        """Rename an existing custom command."""
        if ctx.guild is None:
            await ctx.reply("This command can only be used in a guild.")
            return

        if not VALID_COMMAND_NAME.match(new_name):
            await ctx.reply(f"`{new_name}` is not a valid command name. Use only letters, numbers, underscores, and hyphens.")
            return

        result = await self.bot.database_manager.rename_custom_command(guild_id=ctx.guild.id, old_name=old_name, new_name=new_name)
        if not result:
            await ctx.reply(f"Failed to rename `{old_name}` to `{new_name}`. Ensure the old command exists and the new name is not already taken.")
            return

        await ctx.reply(f"Command `{old_name}` has been renamed to `{new_name}`.")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(CustomCommand(bot))
