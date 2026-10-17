from __future__ import annotations

import functools
import inspect
import logging
import math
import re
from typing import TYPE_CHECKING, Annotated

import discord
from colorama import Fore
from discord.ext import commands

from core import BaseLayoutView, PaginationView
from core.utils.database.models import CustomCommand as CustomCommandModel

from .jinja import SandboxRenderError, render_sandboxed, validate_template
from .variables import Channel, Member, Message, Server, ServerDatabase

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from core import Bot

VALID_COMMAND_NAME = re.compile(r"^[a-z0-9_-]{1,32}$", re.IGNORECASE)

_log = logging.getLogger(__name__)
DISCORD_MESSAGE_LIMIT = 2000
PAGE_SIZE = 6
PREVIEW_LIMIT = 70
DETAIL_RESPONSE_LIMIT = 1500
LOGS_SHOWN = 10
LOG_ENTRY_LIMIT = 300
SELECT_LIMIT = 25

CUSTOM_COMMAND_HELP = r"""
# Custom Commands Overview
The custom command system allows you to create dynamic, personalized commands and autoresponders for your server using the **Jinja2** templating language.

## How it works
When a user triggers a custom command, the bot processes your template and sends the resulting text or adds reactions.
You can insert variables (like the user's name), create conditions (`if`/`else`), and manipulate text.

**Basic Syntax:**
- `{{ ... }}` : Prints the result of a variable (e.g., `{{ author.name }}`).
- `{% ... %}` : Executes logic like loops, conditions, or actions (`{% do message.add_reaction('👋') %}`).

*Note: Templates are strictly sandboxed. Infinite loops, heavy math, and external imports are disabled to keep the bot safe and responsive.*
"""


def _make_help_embed(title: str, body: str) -> discord.Embed:
    return discord.Embed(title=title, description=body, color=discord.Color.blurple())


CUSTOM_COMMAND_VARIABLES_PAGES = [
    _make_help_embed(
        "1. Author & Message (`author`, `message`)",
        inspect.cleandoc("""
        Information and actions for the member who triggered the command and their message.

        **`author` (Triggering Member)**
        - `author`: Stringifies to username (`{{ author }}`)
        - `author.id`: Discord user ID (`int`)
        - `author.name`: Username (e.g., `user123`)
        - `author.display_name`: Server nickname or global display name
        - `author.nick`: Server nickname (`None` if not set)
        - `author.mention`: Mentions the member (`<@id>`)
        - `author.avatar_url`: Link to their display avatar
        - `author.roles`: List of `Role` objects (excludes `@everyone`)

        **`author` Actions (use with `{% do ... %}`)**
        - `{% do author.add_role(role_id, reason='...') %}`: Assigns a safe role below the bot
        - `{% do author.remove_role(role_id, reason='...') %}`: Removes a role
        - `{% do author.kick(reason='...') %}`: Kicks the member (if bot has permission)
        - `{% do author.ban(reason='...', delete_message_days=0) %}`: Bans the member (0-7 days)

        **`message` (Triggering Message)**
        - `message.id`: Discord message ID (`int`)
        - `message.content`: Raw message text (`str`)
        - `{% do message.add_reaction('👋') %}`: Adds an emoji reaction to the message
        """),
    ),
    _make_help_embed(
        "2. Server (`guild`)",
        inspect.cleandoc("""
        Properties for the server where the command was triggered.

        **Identity & Branding**
        - `guild`: Stringifies to server name (`{{ guild }}`)
        - `guild.id`: Server ID (`int`)
        - `guild.name`: Server name (`str`)
        - `guild.description`: Server description (`None` if not set)
        - `guild.vanity_url`: Vanity invite code (`None` if not set)
        - `guild.preferred_locale`: Server language code (e.g., `en_US`)

        **Stats & Boosts**
        - `guild.member_count`: Total member count
        - `guild.premium_tier`: Boost level (`0`-`3`)
        - `guild.premium_subscription_count`: Total server boosts
        - `guild.afk_timeout`: AFK timeout in seconds

        **Media URLs (`None` if not set)**
        - `guild.icon_url` / `guild.icon`: Server icon URL
        - `guild.banner_url`: Server banner URL
        - `guild.splash`: Invite splash image URL
        - `guild.discovery_splash`: Discovery splash image URL
        """),
    ),
    _make_help_embed(
        "3. Channel & Roles (`channel`, `Role`)",
        inspect.cleandoc("""
        Properties for the current channel, its parent category, and member roles.

        **`channel` (Current Channel)**
        - `channel`: Stringifies to channel name (`{{ channel }}`)
        - `channel.id`: Channel ID (`int`)
        - `channel.name`: Channel name (e.g., `general`)
        - `channel.mention`: Clickable channel mention (`<#id>`)
        - `channel.jump_url`: Direct link to the channel
        - `channel.type`: Channel type name (e.g., `text`, `voice`, `news`)
        - `channel.position`: Position in the channel list (`int`)
        - `channel.category`: Parent category as a `Channel` object (`None` if uncategorized)

        **`Role` Objects (via `author.roles`)**
        - `role.id`: Role ID (`int`)
        - `role.name`: Role name (`str`)
        - `role.mention`: Role mention (`<@&id>`)
        - `role.color`: Role color (`#rrggbb`)
        - `role.position`: Hierarchy position (`int`)
        - `role.hoist`: `True` if displayed separately
        - `role.managed`: `True` if managed by an integration/bot
        - `role.mentionable`: `True` if mentionable
        """),
    ),
    _make_help_embed(
        "4. Server Database (`database`)",
        inspect.cleandoc("""
        Persist custom key-value data across command runs in your server.
        Keys can use letters, numbers, `_`, and `-` (up to 64 chars); values are strings up to 2,000 chars.

        **Reading Data**
        - `database.get('key', 'default')`: Returns the stored string, or `'default'` (`None` if omitted)
        - `database.exists('key')`: Returns `True` if the key exists, else `False`

        **Writing & Deleting Data (use with `{% do ... %}`)**
        - `{% do database.set('key', value) %}`: Saves `value` as a string
        - `{% do database.delete('key') %}`: Deletes the key

        **Example: Persistent Counter**
        ```jinja
        {% set count = (database.get('uses', '0') | int) + 1 %}
        {% do database.set('uses', count) %}
        This command has been used {{ count }} times!
        ```
        """),
    ),
    _make_help_embed(
        "5. Logic: Conditionals, Loops & Filters",
        inspect.cleandoc("""
        Combine variables, conditions, loops, and filters to build dynamic responses.

        **Conditionals (`if` / `elif` / `else`)**
        ```jinja
        {% if author.nick %}
          Hey {{ author.nick }}!
        {% elif guild.premium_tier >= 2 %}
          Welcome to {{ guild.name }}, {{ author.display_name }}!
        {% else %}
          Hello, {{ author.name }}!
        {% endif %}
        ```

        **Loops (`for`)**
        ```jinja
        Your roles:
        {% for role in author.roles %}
        - {{ role.name }}
        {% else %}
        You have no roles yet!
        {% endfor %}
        ```

        **Useful Filters & String Methods**
        - `{{ text | lower }}` / `{{ text | upper }}` / `{{ text | title }}`: Change case
        - `{{ text | trim }}`: Strip leading/trailing whitespace
        - `{{ text | length }}`: Count characters in a string or items in a list
        - `{{ value | int }}`: Convert a string to an integer (e.g., for math)
        - `{{ value | default('fallback') }}`: Use fallback if value is undefined/empty
        - `{{ list | join(', ') }}`: Join list items with a separator
        - `{{ message.content.split()[1:] | join(' ') }}`: Everything after the command trigger
        """),
    ),
]

CUSTOM_COMMAND_EXAMPLES_PAGES = [
    _make_help_embed(
        "1. Examples: Replies, Reactions & Server Info",
        inspect.cleandoc("""
        **Welcome Reply + Reaction**
        ```jinja
        {% do message.add_reaction('👋') -%}
        Welcome to **{{ guild.name }}**, {{ author.mention }}! You are one of our **{{ guild.member_count }}** members.
        ```

        **Silent Reaction-Only Autoresponder (Untick *Require prefix*)**
        ```jinja
        {% do message.add_reaction('🔥') %}
        ```

        **Server Status Card**
        ```jinja
        📊 **{{ guild.name }}**
        • Members: **{{ guild.member_count }}** ({{ 1000 - (guild.member_count or 0) }} until 1,000!)
        • Boosts: **{{ guild.premium_subscription_count or 0 }}** (Tier {{ guild.premium_tier }})
        {% if guild.vanity_url %}• Invite: [https://discord.gg/](https://discord.gg/){{ guild.vanity_url }}{% endif %}
        ```
        """),
    ),
    _make_help_embed(
        "2. Examples: Command Arguments & Text Formatting",
        inspect.cleandoc("""
        Extract words typed after the command trigger using `message.content.split()[1:]`.

        **Echo / Announcement Command (with required argument check)**
        ```jinja
        {% set args = message.content.split()[1:] -%}
        {% if not args -%}
          ❌ Usage: `say <your message>`
        {% else -%}
          📣 **{{ author.display_name }} says:** {{ args | join(' ') }}
        {% endif %}
        ```

        **Shout & Word Counter**
        ```jinja
        {% set text = message.content.split()[1:] | join(' ') -%}
        {% if text -%}
          🔊 {{ text | upper }}!!! ({{ text.split() | length }} words, {{ text | length }} chars)
        {% else -%}
          Give me something to shout!
        {% endif %}
        ```
        """),
    ),
    _make_help_embed(
        "3. Examples: Role Checks & Self-Assignable Roles",
        inspect.cleandoc("""
        Use `author.roles | map(attribute='id') | list` to check if a member has a role.

        **Toggle a Self-Assignable Role (replace `123456789012345678` with your Role ID)**
        ```jinja
        {% set role_id = 123456789012345678 -%}
        {% set my_roles = author.roles | map(attribute='id') | list -%}
        {% if role_id in my_roles -%}
          {% do author.remove_role(role_id, reason='Custom command role toggle') -%}
          **[`-`]** Removed the role from {{ author.display_name }}!
        {% else -%}
          {% do author.add_role(role_id, reason='Custom command role toggle') -%}
          **[`+`]** Added the role to {{ author.display_name }}!
        {% endif %}
        ```

        **List a Member's Roles**
        ```jinja
        {% if author.roles -%}
          **{{ author.display_name }}'s roles ({{ author.roles | length }}):**
          {{ author.roles | map(attribute='name') | join(', ') }}
        {% else -%}
          You don't have any special roles yet!
        {% endif %}
        ```
        """),
    ),
    _make_help_embed(
        "4. Examples: Persistent Database (`database`)",
        inspect.cleandoc("""
        Store server-wide counters or per-user stats using `~` to combine strings.

        **Global Cookie Jar Counter**
        ```jinja
        {% set total = (database.get('cookie_jar', '0') | int) + 1 -%}
        {% do database.set('cookie_jar', total) -%}
        🍪 {{ author.display_name }} added a cookie! The jar now has **{{ total }}** cookies.
        ```

        **Per-User Check-In Counter**
        ```jinja
        {% set key = 'checkins_' ~ author.id -%}
        {% set count = (database.get(key, '0') | int) + 1 -%}
        {% do database.set(key, count) -%}
        ✅ **{{ author.display_name }}**, you have checked in **{{ count }}** time{{ '' if count == 1 else 's' }}!
        ```

        **Configurable Server Notice (`!notice` to view, `!notice <text>` to update)**
        ```jinja
        {% set new_notice = message.content.split()[1:] | join(' ') -%}
        {% if new_notice -%}
          {% do database.set('server_notice', new_notice) -%}
          📌 Updated the server notice!
        {% else -%}
          📌 **Current Notice:** {{ database.get('server_notice', 'No notice set yet.') }}
        {% endif %}
        ```
        """),
    ),
    _make_help_embed(
        "5. Examples: Channel & Context Conditions",
        inspect.cleandoc("""
        Tailor responses based on the channel, category, or keywords in the message.

        **Channel-Specific Command Redirect**
        ```jinja
        {% if channel.name != 'bot-commands' -%}
          Please use this command inside `#bot-commands` instead of {{ channel.mention }}!
        {% else -%}
          ✅ Running command in {{ channel.mention }}!
        {% endif %}
        ```

        **Keyword Help Autoresponder**
        ```jinja
        {% set msg = message.content | lower -%}
        {% if 'apply' in msg or 'staff' in msg -%}
          📝 Looking to apply for staff, {{ author.display_name }}? Check the pinned message in `#applications`!
        {% elif 'support' in msg or 'ticket' in msg -%}
          🎫 Need help? Open a ticket in `#support` and a moderator will be right with you.
        {% endif %}
        ```
        """),
    ),
    _make_help_embed(
        "6. Examples: Whitespace Control & Sandbox Limits",
        inspect.cleandoc("""
        **Removing Extra Blank Lines (`-%}`)**
        Add a hyphen (`-%}`) to the end of `{% set %}` or `{% do %}` tags so they don't add blank lines to your message:
        ```jinja
        {% set name = author.nick or author.display_name -%}
        {% do message.add_reaction('✨') -%}
        Hello, {{ name }}!
        ```

        **Sandbox Limits to Keep in Mind**
        - **Message length**: Responses over 2,000 characters are automatically truncated.
        - **Loop steps**: Loops and macros are capped at 20,000 total steps and a 1.5s timeout.
        - **Sequence & math limits**: Large string repetitions (`'a' * 100000`), power operators (`**`), `%` string formatting, and `import`/`include`/`extends` tags are disabled.
        """),
    ),
]


def trigger_text(command: CustomCommandModel, prefix: str) -> str:
    return f"{prefix}{command['name']}" if command.get("require_prefix", True) else command["name"]


def preview(response: str) -> str:
    flat = " ".join(response.split()).replace("`", "'")
    return flat if len(flat) <= PREVIEW_LIMIT else f"{flat[: PREVIEW_LIMIT - 1]}…"


class PanelButton(discord.ui.Button):
    def __init__(self, handler: Callable[[discord.Interaction[Bot]], Awaitable[None]], **kwargs) -> None:
        super().__init__(**kwargs)
        self.handler = handler

    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        await self.handler(interaction)


class CustomCommandVariablesButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Variables", style=discord.ButtonStyle.gray)

    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        view = PaginationView(author=interaction.user, items=CUSTOM_COMMAND_VARIABLES_PAGES, hide_quit_button=True)
        await interaction.response.send_message(embed=CUSTOM_COMMAND_VARIABLES_PAGES[0], view=view, ephemeral=True)


class CustomCommandExamplesButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Examples", style=discord.ButtonStyle.gray)

    async def callback(self, interaction: discord.Interaction[Bot]) -> None:
        view = PaginationView(author=interaction.user, items=CUSTOM_COMMAND_EXAMPLES_PAGES, hide_quit_button=True)
        await interaction.response.send_message(embed=CUSTOM_COMMAND_EXAMPLES_PAGES[0], view=view, ephemeral=True)


class CommandEditorModal(discord.ui.Modal):
    def __init__(
        self,
        *,
        panel: CustomCommandPanel,
        guild: discord.Guild,
        existing: CustomCommandModel | None = None,
    ) -> None:
        super().__init__(title=f"Edit: {existing['name']}" if existing else "Create custom command")
        self.panel = panel
        self.existing = existing
        self.name_input: discord.ui.TextInput | None = None

        if existing is None:
            self.name_input = discord.ui.TextInput(
                label="Command name",
                placeholder="welcome",
                max_length=32,
                required=True,
            )
            self.add_item(self.name_input)

        self.response_input = discord.ui.TextInput(
            label="Response template",
            placeholder="Hello {{ author.display_name }}!",
            style=discord.TextStyle.paragraph,
            max_length=3000,
            default=existing["response"] if existing else None,
            required=True,
        )
        self.add_item(self.response_input)

        ignored_roles = existing["ignored_roles"] if existing else []
        ignored_channels = existing["ignored_channels"] if existing else []

        self.roles_select = discord.ui.RoleSelect(
            min_values=0,
            max_values=SELECT_LIMIT,
            required=False,
            default_values=[discord.Object(id=role_id) for role_id in ignored_roles if guild.get_role(role_id) is not None][:SELECT_LIMIT],
        )
        self.add_item(
            discord.ui.Label(
                text="Ignored roles",
                description="Members with these roles can't trigger the command.",
                component=self.roles_select,
            )
        )

        self.channels_select = discord.ui.ChannelSelect(
            min_values=0,
            max_values=SELECT_LIMIT,
            required=False,
            default_values=[discord.Object(id=channel_id) for channel_id in ignored_channels if guild.get_channel_or_thread(channel_id) is not None][
                :SELECT_LIMIT
            ],
        )
        self.add_item(
            discord.ui.Label(
                text="Ignored channels",
                description="The command won't trigger in these channels (or their threads).",
                component=self.channels_select,
            )
        )

        self.prefix_checkbox = discord.ui.Checkbox(default=existing.get("require_prefix", True) if existing else True)
        self.add_item(
            discord.ui.Label(
                text="Require prefix",
                description="Unticked: triggers when a message starts with the name (no prefix needed).",
                component=self.prefix_checkbox,
            )
        )

    def validate(self, interaction: discord.Interaction[Bot], name: str, response: str, require_prefix: bool) -> str | None:
        if not VALID_COMMAND_NAME.match(name):
            return f"`{name}` is not a valid command name. Use only letters, numbers, underscores, and hyphens."

        try:
            validate_template(response)
        except SandboxRenderError as error:
            return f"Template error: {error}"

        if require_prefix:
            existing_bot_command = interaction.client.get_command(name)
            if existing_bot_command is not None:
                help_line = f"\n-# Help: {existing_bot_command.help}" if existing_bot_command.help else ""
                return (
                    f"A command with the name `{name}` already exists as a bot command. Pick a different name or untick *Require prefix*.{help_line}"
                )
        return None

    async def on_submit(self, interaction: discord.Interaction[Bot]) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("This can only be used in a guild.", ephemeral=True)
            return

        if self.existing is not None:
            name = self.existing["name"]
        elif self.name_input is not None:
            name = self.name_input.value.strip().lower()
        else:
            return

        response = self.response_input.value.strip()
        require_prefix = self.prefix_checkbox.value

        error = self.validate(interaction, name, response, require_prefix)
        if error is not None:
            await interaction.response.send_message(error, ephemeral=True)
            return

        options = {
            "guild_id": interaction.guild_id,
            "name": name,
            "response": response,
            "ignored_roles": [role.id for role in self.roles_select.values],
            "ignored_channels": [channel.id for channel in self.channels_select.values],
            "require_prefix": require_prefix,
        }
        database = interaction.client.database
        if self.existing is None:
            success = await database.add_custom_command(**options)
            failure = f"A command with the name `{name}` already exists."
            notice = f"Custom command `{name}` has been created."
        else:
            success = await database.edit_custom_command(**options)
            failure = f"No command with the name `{name}` exists."
            notice = f"Custom command `{name}` has been updated."

        if not success:
            await interaction.response.send_message(failure, ephemeral=True)
            return

        await self.panel.after_save(interaction, name, notice)


class CustomCommandPanel(BaseLayoutView):
    def __init__(
        self,
        *,
        author: discord.User | discord.Member,
        guild: discord.Guild,
        prefix: str,
        custom_commands: list[CustomCommandModel],
        selected: str | None = None,
    ) -> None:
        super().__init__(author=author)
        self.guild = guild
        self.prefix = prefix
        self.custom_commands = custom_commands
        self.selected = selected
        self.mode = "detail" if selected else "list"
        self.page = 0
        self.logs: list[str] = []
        self.confirm_delete = False
        self.build()

    def find(self, name: str | None) -> CustomCommandModel | None:
        return next((command for command in self.custom_commands if command["name"] == name), None)

    def build(self) -> None:
        self.clear_items()
        if self.mode == "detail" and self.find(self.selected) is None:
            self.mode, self.selected, self.confirm_delete = "list", None, False

        match self.mode:
            case "detail":
                items = self.detail_items()
            case "logs":
                items = self.logs_items()
            case _:
                items = self.list_items()
        self.add_item(discord.ui.Container(*items))

    def describe(self, command: CustomCommandModel) -> str:
        badges = []
        if not command.get("enabled", True):
            badges.append("disabled")
        if not command.get("require_prefix", True):
            badges.append("no prefix")
        suffix = f" · {' · '.join(badges)}" if badges else ""
        return f"**`{trigger_text(command, self.prefix)}`**{suffix}\n-# {preview(command['response'])}"

    def list_items(self) -> list[discord.ui.Item]:
        pages = max(1, math.ceil(len(self.custom_commands) / PAGE_SIZE))
        self.page = max(0, min(self.page, pages - 1))
        chunk = self.custom_commands[self.page * PAGE_SIZE : (self.page + 1) * PAGE_SIZE]

        items: list[discord.ui.Item] = [
            discord.ui.TextDisplay(f"## Custom Commands\n-# {len(self.custom_commands)} total · prefix `{self.prefix}`"),
            discord.ui.Separator(),
        ]

        if not chunk:
            items.append(discord.ui.TextDisplay(CUSTOM_COMMAND_HELP.strip()))

        items.extend(
            discord.ui.Section(
                self.describe(command),
                accessory=PanelButton(functools.partial(self.open_detail, command["name"]), label="Manage"),
            )
            for command in chunk
        )

        if pages > 1:
            items.append(
                discord.ui.ActionRow(
                    PanelButton(self.previous_page, label="◀", disabled=self.page == 0),
                    discord.ui.Button(label=f"{self.page + 1}/{pages}", disabled=True),
                    PanelButton(self.next_page, label="▶", disabled=self.page >= pages - 1),
                )
            )

        items.append(discord.ui.Separator())
        items.append(
            discord.ui.ActionRow(
                PanelButton(self.create, label="Create", style=discord.ButtonStyle.green),
                CustomCommandVariablesButton(),
                CustomCommandExamplesButton(),
                PanelButton(self.show_logs, label="Logs"),
            )
        )
        return items

    def detail_items(self) -> list[discord.ui.Item]:
        command = self.find(self.selected)
        if TYPE_CHECKING:
            assert command is not None

        enabled = command.get("enabled", True)
        require_prefix = command.get("require_prefix", True)
        response = command["response"]
        shown = response if len(response) <= DETAIL_RESPONSE_LIMIT else f"{response[:DETAIL_RESPONSE_LIMIT]}\n…"

        items: list[discord.ui.Item] = [
            discord.ui.TextDisplay(
                f"## `{trigger_text(command, self.prefix)}`\n"
                f"-# {'enabled' if enabled else 'disabled'} · "
                f"{'requires the prefix' if require_prefix else 'triggers without a prefix'}"
            ),
            discord.ui.TextDisplay(f"```jinja\n{shown.replace('```', chr(39) * 3)}\n```"),
        ]

        roles = " ".join(f"<@&{role_id}>" for role_id in command["ignored_roles"])
        channels = " ".join(f"<#{channel_id}>" for channel_id in command["ignored_channels"])
        ignored = [
            text
            for text in (
                f"**Ignored roles:** {roles}" if roles else "",
                f"**Ignored channels:** {channels}" if channels else "",
            )
            if text
        ]
        if ignored:
            items.append(discord.ui.TextDisplay("\n".join(ignored)))

        items.append(discord.ui.Separator())
        if self.confirm_delete:
            items.append(discord.ui.TextDisplay("**Delete this command?** This can't be undone."))
            items.append(
                discord.ui.ActionRow(
                    PanelButton(self.delete_confirmed, label="Confirm delete", style=discord.ButtonStyle.red),
                    PanelButton(self.cancel_delete, label="Cancel"),
                )
            )
        else:
            items.append(
                discord.ui.ActionRow(
                    PanelButton(self.edit, label="Edit", style=discord.ButtonStyle.blurple),
                    PanelButton(self.toggle, label="Disable" if enabled else "Enable"),
                    PanelButton(self.ask_delete, label="Delete", style=discord.ButtonStyle.red),
                    PanelButton(self.back, label="Back"),
                )
            )
        return items

    def logs_items(self) -> list[discord.ui.Item]:
        recent = self.logs[-LOGS_SHOWN:][::-1]
        body = "\n".join(f"- {entry[:LOG_ENTRY_LIMIT]}" for entry in recent) or "*No activity yet.*"
        return [
            discord.ui.TextDisplay("## Recent activity"),
            discord.ui.TextDisplay(body),
            discord.ui.Separator(),
            discord.ui.ActionRow(
                PanelButton(self.back, label="Back"),
                PanelButton(self.clear_logs, label="Clear logs", style=discord.ButtonStyle.red, disabled=not self.logs),
            ),
        ]

    async def render(self, interaction: discord.Interaction[Bot], *, reload: bool = False) -> None:
        database = interaction.client.database
        if reload:
            self.custom_commands = await database.get_custom_commands(self.guild.id)
            if self.mode == "logs":
                self.logs = await database.get_custom_command_logs(guild_id=self.guild.id)

        self.build()
        if interaction.response.is_done():
            await interaction.edit_original_response(view=self)
        else:
            await interaction.response.edit_message(view=self)

    async def after_save(self, interaction: discord.Interaction[Bot], name: str, notice: str) -> None:
        self.mode, self.selected, self.confirm_delete = "detail", name, False
        await self.render(interaction, reload=True)
        await interaction.followup.send(notice, ephemeral=True)

    async def open_detail(self, name: str, interaction: discord.Interaction[Bot]) -> None:
        self.mode, self.selected, self.confirm_delete = "detail", name, False
        await self.render(interaction)

    async def previous_page(self, interaction: discord.Interaction[Bot]) -> None:
        self.page -= 1
        await self.render(interaction)

    async def next_page(self, interaction: discord.Interaction[Bot]) -> None:
        self.page += 1
        await self.render(interaction)

    async def back(self, interaction: discord.Interaction[Bot]) -> None:
        self.mode, self.selected, self.confirm_delete = "list", None, False
        await self.render(interaction, reload=True)

    async def show_logs(self, interaction: discord.Interaction[Bot]) -> None:
        self.mode = "logs"
        await self.render(interaction, reload=True)

    async def clear_logs(self, interaction: discord.Interaction[Bot]) -> None:
        await interaction.client.database.clear_custom_command_logs(guild_id=self.guild.id)
        await self.render(interaction, reload=True)

    async def create(self, interaction: discord.Interaction[Bot]) -> None:
        await interaction.response.send_modal(CommandEditorModal(panel=self, guild=self.guild))

    async def edit(self, interaction: discord.Interaction[Bot]) -> None:
        command = self.find(self.selected)
        if command is None:
            await self.render(interaction, reload=True)
            return
        await interaction.response.send_modal(CommandEditorModal(panel=self, guild=self.guild, existing=command))

    async def toggle(self, interaction: discord.Interaction[Bot]) -> None:
        command = self.find(self.selected)
        if command is not None:
            await interaction.client.database.edit_custom_command(
                guild_id=self.guild.id,
                name=command["name"],
                enabled=not command.get("enabled", True),
            )
        await self.render(interaction, reload=True)

    async def ask_delete(self, interaction: discord.Interaction[Bot]) -> None:
        self.confirm_delete = True
        await self.render(interaction)

    async def cancel_delete(self, interaction: discord.Interaction[Bot]) -> None:
        self.confirm_delete = False
        await self.render(interaction)

    async def delete_confirmed(self, interaction: discord.Interaction[Bot]) -> None:
        name = self.selected
        deleted = bool(name) and await interaction.client.database.delete_custom_command(guild_id=self.guild.id, name=name)
        self.mode, self.selected, self.confirm_delete = "list", None, False
        await self.render(interaction, reload=True)
        await interaction.followup.send(
            f"Custom command `{name}` has been deleted." if deleted else "That command no longer exists.",
            ephemeral=True,
        )


class CC(commands.Cog, name="Custom Commands"):
    """Manage custom commands."""

    help_emoji = "\N{JIGSAW PUZZLE PIECE}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self._cooldown_mapping = commands.CooldownMapping.from_cooldown(10, 10.0, commands.BucketType.guild)
        _log.debug("Cog loaded: %s", self.__class__.__name__)

    async def open_panel(self, ctx: commands.Context[Bot], *, selected: str | None = None) -> None:
        if TYPE_CHECKING:
            assert ctx.guild is not None

        custom_commands = await self.bot.database.get_custom_commands(ctx.guild.id)
        layout = CustomCommandPanel(
            author=ctx.author,
            guild=ctx.guild,
            prefix=ctx.clean_prefix,
            custom_commands=custom_commands,
            selected=selected,
        )
        await ctx.reply(view=layout, allowed_mentions=discord.AllowedMentions.none())

    @commands.group(name="cc", aliases=["customcommand"], invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def cc(self, ctx: commands.Context[Bot]) -> None:
        """Manage custom commands."""
        await self.open_panel(ctx)

    @cc.command(name="manage")
    @commands.has_permissions(administrator=True)
    async def manage(self, ctx: commands.Context[Bot]) -> None:
        """Open the custom-command management panel."""
        await self.open_panel(ctx)

    @cc.command(name="logs", aliases=["log"])
    @commands.has_permissions(administrator=True)
    async def logs(self, ctx: commands.Context[Bot]) -> None:
        """View the custom command logs."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        logs = await self.bot.database.get_custom_command_logs(guild_id=ctx.guild.id)
        if not logs:
            await ctx.send("No custom command logs found.")
            return

        embeds = [discord.Embed(description="\n".join(chunk), color=discord.Color.blue()) for chunk in discord.utils.as_chunks(logs[::-1], 10)]
        view = PaginationView(author=ctx.author, items=embeds)
        await view.start(ctx)

    def prepare_context(self, ctx: commands.Context[Bot]) -> dict[str, object]:
        if TYPE_CHECKING:
            assert ctx.guild is not None
            assert isinstance(ctx.channel, discord.abc.GuildChannel)
            assert isinstance(ctx.author, discord.Member)

        internal_db = self.bot.database.cc_internal_database
        return {
            "channel": Channel(_channel=ctx.channel),
            "guild": Server(_guild=ctx.guild),
            "author": Member(_member=ctx.author),
            "message": Message(_message=ctx.message),
            "database": ServerDatabase(
                guild=ctx.guild,
                get_func=internal_db.get,
                set_func=internal_db.set,
                delete_func=internal_db.delete,
                exists_func=internal_db.exists,
            ),
        }

    @staticmethod
    def _log_entry(message: discord.Message, name: str, *, error: str | None = None) -> str:
        author = discord.utils.escape_markdown(str(message.author))
        entry = f"<t:{int(message.created_at.timestamp())}:R> {author} (`{message.author.id}`) ran `{name}` in <#{message.channel.id}>"
        return f"{entry} - failed: {' '.join(error.split())[:200]}" if error else entry

    async def _render_custom_command(self, ctx: commands.Context[Bot], response: str, name: str) -> str | None:
        if TYPE_CHECKING:
            assert ctx.guild is not None
            assert isinstance(ctx.author, discord.Member)

        try:
            return await render_sandboxed(response, **self.prepare_context(ctx))
        except Exception as error:
            _log.warning("Custom command %r failed in guild %s", name, ctx.guild.id, exc_info=error)
            reason = str(error) if isinstance(error, SandboxRenderError) else f"{type(error).__name__}: {error}"
            await self.bot.database.push_custom_command_log(
                guild_id=ctx.guild.id,
                log_entry=self._log_entry(ctx.message, name, error=reason),
            )

            if ctx.author.guild_permissions.administrator:
                content = f"```ansi\n{Fore.BLUE}Error while rendering cc id: {name}\n{Fore.RED}{reason[:1200].replace('```', chr(39) * 3)}```"
            else:
                content = "This custom command is currently broken. An admin can check `cc logs` for details."
            await ctx.reply(content, allowed_mentions=discord.AllowedMentions.none())
            return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:  # noqa: PLR0911
        if message.guild is None or message.author.bot or not message.content or not isinstance(message.author, discord.Member):
            return

        context = await self.bot.get_context(message)
        if context.command is not None:
            return

        prefixed = context.prefix is not None and bool(context.invoked_with)
        word = context.invoked_with if prefixed else message.content.split(maxsplit=1)[0]
        name = (word or "").lower()
        if not VALID_COMMAND_NAME.match(name):
            return

        command = await self.bot.database.get_custom_command_cached(guild_id=message.guild.id, name=name)
        if command is None or not command.get("enabled", True):
            return
        if command.get("require_prefix", True) != prefixed:
            return

        channel = message.channel
        channel_ids = {channel.id, getattr(channel, "parent_id", None), getattr(channel, "category_id", None)}
        if channel_ids.intersection(command["ignored_channels"]):
            return
        if any(role.id in command["ignored_roles"] for role in message.author.roles):
            return

        bucket = self._cooldown_mapping.get_bucket(message)
        retry_after = bucket.update_rate_limit() if bucket is not None else None
        if retry_after:
            _log.info(
                "Custom command '%s' invoked too quickly in guild %s (%s). Retry after %.2f seconds.",
                name,
                message.guild.name,
                message.guild.id,
                retry_after,
            )
            return

        rendered = await self._render_custom_command(context, command["response"], name)
        if rendered is None:
            return

        await self.bot.database.push_custom_command_log(guild_id=message.guild.id, log_entry=self._log_entry(message, name))
        cleaned = rendered.strip()
        if not cleaned:
            return
        if len(cleaned) > DISCORD_MESSAGE_LIMIT:
            cleaned = f"{cleaned[:1997]}..."
        await message.channel.send(cleaned, allowed_mentions=discord.AllowedMentions.none())

    @cc.command(name="edit")
    @commands.has_permissions(administrator=True)
    async def edit_custom_command(
        self,
        ctx: commands.Context[Bot],
        name: Annotated[str, commands.clean_content] = commands.parameter(description="The name of the custom command to edit."),
    ) -> None:
        """Edit an existing custom command."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        name = name.lower()
        command = await self.bot.database.get_custom_command(guild_id=ctx.guild.id, name=name)
        if command is None:
            await ctx.reply(f"No command with the name `{name}` exists.")
            return

        await self.open_panel(ctx, selected=name)

    @cc.command(name="delete")
    @commands.has_permissions(administrator=True)
    async def delete_custom_command(
        self,
        ctx: commands.Context[Bot],
        name: Annotated[str, commands.clean_content] = commands.parameter(description="The name of the custom command to delete."),
    ) -> None:
        """Delete an existing custom command."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        name = name.lower()
        result = await self.bot.database.delete_custom_command(guild_id=ctx.guild.id, name=name)
        if not result:
            await ctx.reply(f"No command with the name `{name}` exists.")
            return

        await ctx.reply(f"Command `{name}` deleted.")

    @cc.command(name="rename")
    @commands.has_permissions(administrator=True)
    async def rename_custom_command(
        self,
        ctx: commands.Context[Bot],
        old_name: Annotated[str, commands.clean_content] = commands.parameter(description="The current name of the custom command."),
        new_name: Annotated[str, commands.clean_content] = commands.parameter(description="The new name for the custom command."),
    ) -> None:
        """Rename an existing custom command."""
        if TYPE_CHECKING:
            assert ctx.guild is not None

        old_name, new_name = old_name.lower(), new_name.lower()
        if not VALID_COMMAND_NAME.match(new_name):
            await ctx.reply(f"`{new_name}` is not a valid command name. Use only letters, numbers, underscores, and hyphens.")
            return

        command = await self.bot.database.get_custom_command(guild_id=ctx.guild.id, name=old_name)
        if command is None:
            await ctx.reply(f"No command with the name `{old_name}` exists.")
            return

        if command.get("require_prefix", True) and self.bot.get_command(new_name) is not None:
            await ctx.reply(f"`{new_name}` is already a bot command. Please choose a different name.")
            return

        result = await self.bot.database.rename_custom_command(guild_id=ctx.guild.id, old_name=old_name, new_name=new_name)
        if not result:
            await ctx.reply(f"Failed to rename `{old_name}` to `{new_name}`. The new name may already be taken.")
            return

        await ctx.reply(f"Command `{old_name}` has been renamed to `{new_name}`.")


async def setup(bot: Bot) -> None:
    await bot.add_cog(CC(bot))
