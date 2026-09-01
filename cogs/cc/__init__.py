from __future__ import annotations

import re
import traceback
from enum import Enum
from typing import TYPE_CHECKING, Annotated

import discord
from colorama import Fore
from discord.ext import commands

from core.utils.database_manager.models import CustomCommand as CustomCommandModel

from .jinja import render_sandboxed
from .variables import JinjaChannel, JinjaGuild, JinjaMember, JinjaMessage

if TYPE_CHECKING:
    from core.bot import Parrot

VALID_COMMAND_NAME = re.compile(r"^[a-z0-9_-]{1,32}$", re.IGNORECASE)


def format_sandbox_error(error: Exception) -> str:
    """Format a sandbox error for display."""
    tb = traceback.format_exception(type(error), error, error.__traceback__)
    return "".join(tb)


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

        # self.ignored_roles_select = discord.ui.RoleSelect(placeholder="Select roles to ignore")
        # self.ignored_channels_select = discord.ui.ChannelSelect(placeholder="Select channels to ignore")

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


class CustomCommand(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.group(name="cc", aliases=["customcommand"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def cc(self, ctx: commands.Context[Parrot]) -> None:
        """Manage custom commands."""
        await self.send_panel(ctx)

    async def _build_and_send_panel(self, ctx: commands.Context[Parrot], pages: list[str], select_menu: CustomCommandSelect | None) -> None:
        """Build and send the management panel with appropriate pagination."""
        embed = discord.Embed(title="Custom Command Management Panel", description="\n".join(pages) if pages else None)

        buttons: list[discord.ui.Item] = [CreateCustomCommandButton()]
        if select_menu:
            buttons.append(select_menu)

        total_content_length = len("".join(pages))
        if total_content_length < 1900:
            view = discord.ui.View()
            for button in buttons:
                view.add_item(button)
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.bot.paginate(ctx, embed=embed, pages=pages, additional_buttons=buttons)

    async def send_panel(self, ctx: commands.Context[Parrot]) -> None:
        if ctx.guild is None:
            return

        custom_commands = await self.bot.database_manager.get_custom_commands(ctx.guild.id)
        pages = [f"- {command['name']}: {command['response'][:80]}{'...' if len(command['response']) > 80 else ''}" for command in custom_commands]
        select_menu = CustomCommandSelect(custom_commands=custom_commands) if custom_commands else None

        await self._build_and_send_panel(ctx, pages, select_menu)

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
        if rendered:
            if len(rendered) > 2000:
                rendered = f"{rendered[:1997]}..."
            await message.channel.send(rendered)

    @cc.command(name="create")
    @commands.has_permissions(administrator=True)
    async def create_custom_command(
        self,
        ctx: commands.Context[Parrot],
        name: Annotated[str, commands.clean_content] = commands.parameter(description="The name of the custom command to create."),
    ) -> None:
        """Create a new custom command."""
        button = CreateCustomCommandButton(custom_command_name=name)
        embed = discord.Embed(title="Create Custom Command", description="Fill out the form to create a new custom command.")
        view = discord.ui.View()
        view.add_item(button)
        await ctx.reply(embed=embed, view=view)

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
