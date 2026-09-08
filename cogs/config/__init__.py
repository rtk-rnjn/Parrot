from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Unpack

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from cogs.leveling import Leveling
    from core.bot import Parrot
    from core.utils.database_manager.models import GuildConfiguration


_log = logging.getLogger("bot.cogs.config")


class UpdateBotPrefixModal(discord.ui.Modal, title="Update Bot Prefix"):
    def __init__(self, *, bot_prefix: str) -> None:
        super().__init__()

        self.bot_prefix = bot_prefix

        self.prefix_input = discord.ui.TextInput(
            label="New Bot Prefix",
            placeholder="Enter the new bot prefix here...",
            default=self.bot_prefix,
            required=True,
            max_length=16,
            min_length=1,
        )

        self.add_item(self.prefix_input)

    async def on_submit(self, interaction: discord.Interaction[Parrot]) -> None:
        new_prefix = self.prefix_input.value.strip()
        await interaction.response.defer(ephemeral=True)

        if interaction.guild is None:
            await interaction.followup.send(
                "This command can only be used in a server (guild).",
                ephemeral=True,
            )
            return

        await interaction.client.database.set_command_prefix(
            guild_id=interaction.guild.id,
            command_prefix=new_prefix,
        )

        await interaction.followup.send(
            f"Bot prefix updated to `{new_prefix}`.",
            ephemeral=True,
        )


class ConfigurationLayout(discord.ui.LayoutView):
    action_row = discord.ui.ActionRow()

    def __init__(self, **kwargs: Unpack[GuildConfiguration]) -> None:
        super().__init__()
        self.kwargs = kwargs

        welcome_join_channel_id = kwargs["welcome_config"]["on_member_join_channel_id"]
        self.welcome_join_channel = discord.Object(id=welcome_join_channel_id) if welcome_join_channel_id is not None else None
        welcome_leave_channel_id = kwargs["welcome_config"]["on_member_leave_channel_id"]
        self.welcome_leave_channel = discord.Object(id=welcome_leave_channel_id) if welcome_leave_channel_id is not None else None
        prefix_section_button = discord.ui.Button(label=kwargs["command_prefix"], style=discord.ButtonStyle.green)
        prefix_section_button.callback = self.change_prefix_callback
        prefix_section = discord.ui.Section(
            discord.ui.TextDisplay(
                "### Bot Prefix\n-# The bot prefix is the character(s) that you use to invoke commands. ",
            ),
            accessory=prefix_section_button,
        )

        mute_role_selector = discord.ui.ActionRow(
            discord.ui.RoleSelect(
                placeholder="Select a mute role...",
                min_values=0,
                max_values=1,
            ),
        )
        mute_role_delete_button = discord.ui.Button(
            emoji="\N{WASTEBASKET}",
            style=discord.ButtonStyle.red,
        )
        mute_role_delete_button.callback = self.delete_mute_role_callback
        mute_role_section = discord.ui.Section(
            discord.ui.TextDisplay(
                "### Mute Role\n-# The mute role is the role that is assigned to users when they are muted.",
            ),
            accessory=mute_role_delete_button,
        )

        self.welcome_enable_button = discord.ui.Button(
            label="Enable",
            style=discord.ButtonStyle.success,
            disabled=kwargs["welcome_config"]["enabled"],
        )
        self.welcome_enable_button.callback = self.enable_welcome_callback
        self.welcome_disable_button = discord.ui.Button(
            label="Disable",
            style=discord.ButtonStyle.danger,
            disabled=not kwargs["welcome_config"]["enabled"],
        )
        self.welcome_disable_button.callback = self.disable_welcome_callback
        welcome_toggle_row = discord.ui.ActionRow(self.welcome_enable_button, self.welcome_disable_button)

        self.welcome_join_channel_select = discord.ui.ChannelSelect(
            placeholder="Select the member join channel...",
            channel_types=[discord.ChannelType.text],
            default_values=[self.welcome_join_channel] if self.welcome_join_channel else [],
        )
        self.welcome_join_channel_select.callback = self.set_welcome_join_channel_callback
        self.welcome_leave_channel_select = discord.ui.ChannelSelect(
            placeholder="Select the member leave channel...",
            channel_types=[discord.ChannelType.text],
            default_values=[self.welcome_leave_channel] if self.welcome_leave_channel else [],
        )
        self.welcome_leave_channel_select.callback = self.set_welcome_leave_channel_callback

        self.leveling_enable_button = discord.ui.Button(
            label="Enable",
            style=discord.ButtonStyle.success,
            disabled=kwargs["leveling_config"]["enabled"],
        )
        self.leveling_enable_button.callback = self.enable_leveling_callback
        self.leveling_disable_button = discord.ui.Button(
            label="Disable",
            style=discord.ButtonStyle.danger,
            disabled=not kwargs["leveling_config"]["enabled"],
        )
        self.leveling_disable_button.callback = self.disable_leveling_callback
        leveling_toggle_row = discord.ui.ActionRow(self.leveling_enable_button, self.leveling_disable_button)

        container = discord.ui.Container(
            discord.ui.TextDisplay(
                "## Configuration\n-# This is the configuration panel for the bot. You can change various settings here.\n",
            ),
            discord.ui.Separator(),
            prefix_section,
            discord.ui.Separator(),
            mute_role_section,
            mute_role_selector,
            discord.ui.Separator(),
            discord.ui.TextDisplay("### Welcome Messages\n-# Configure whether join and leave messages are enabled and where they are sent."),
            welcome_toggle_row,
            discord.ui.ActionRow(self.welcome_join_channel_select),
            discord.ui.ActionRow(self.welcome_leave_channel_select),
            discord.ui.Separator(),
            discord.ui.TextDisplay("### Leveling\n-# Enable or disable XP tracking for this server."),
            leveling_toggle_row,
        )

        self.add_item(container)

    async def change_prefix_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        await interaction.response.send_modal(UpdateBotPrefixModal(bot_prefix=self.kwargs["command_prefix"]))

    async def delete_mute_role_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server (guild).",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        await interaction.client.database.delete_mute_role(guild_id=interaction.guild.id)
        await interaction.client.event_scheduler.delete_timer(event_name="mute", metadata_filter={"guild_id": interaction.guild.id}, multiple=True)

        await interaction.followup.send(
            "The mute role has been deleted. Users will no longer be muted until a new mute role is set.",
            ephemeral=True,
        )

    async def _require_administrator(self, interaction: discord.Interaction[Parrot]) -> bool:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only server administrators can change these settings.", ephemeral=True)
            return False
        return True

    async def enable_welcome_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if not await self._require_administrator(interaction):
            return
        assert interaction.guild is not None
        updated = await interaction.client.database.edit_welcome_config(guild_id=interaction.guild.id, enabled=True)
        if not updated:
            await interaction.response.send_message("Welcome messages are not configured for this server.", ephemeral=True)
            return
        self.welcome_enable_button.disabled = True
        self.welcome_disable_button.disabled = False
        await interaction.response.edit_message(view=self)

    async def disable_welcome_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if not await self._require_administrator(interaction):
            return
        assert interaction.guild is not None
        updated = await interaction.client.database.edit_welcome_config(guild_id=interaction.guild.id, enabled=False)
        if not updated:
            await interaction.response.send_message("Welcome messages are not configured for this server.", ephemeral=True)
            return
        self.welcome_enable_button.disabled = False
        self.welcome_disable_button.disabled = True
        await interaction.response.edit_message(view=self)

    async def _send_config_missing(self, interaction: discord.Interaction[Parrot], feature: str) -> None:
        await interaction.response.send_message(
            f"{feature} is not configured for this server.",
            ephemeral=True,
        )

    async def set_welcome_join_channel_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if not await self._require_administrator(interaction):
            return
        assert interaction.guild is not None
        channel = self.welcome_join_channel_select.values[0]
        updated = await interaction.client.database.edit_welcome_config(
            guild_id=interaction.guild.id,
            on_member_join_channel_id=channel.id,
        )
        if not updated:
            await self._send_config_missing(interaction, "Welcome messages")
            return
        await interaction.response.send_message("Welcome join channel updated.", ephemeral=True)

    async def set_welcome_leave_channel_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if not await self._require_administrator(interaction):
            return
        assert interaction.guild is not None
        channel = self.welcome_leave_channel_select.values[0]
        updated = await interaction.client.database.edit_welcome_config(
            guild_id=interaction.guild.id,
            on_member_leave_channel_id=channel.id,
        )
        if not updated:
            await self._send_config_missing(interaction, "Welcome messages")
            return
        await interaction.response.send_message("Welcome leave channel updated.", ephemeral=True)

    async def enable_leveling_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if not await self._require_administrator(interaction):
            return
        assert interaction.guild is not None
        updated = await interaction.client.database.edit_leveling_config(guild_id=interaction.guild.id, enabled=True)
        if not updated:
            await interaction.response.send_message("Leveling is not configured for this server.", ephemeral=True)
            return
        leveling_cog: Leveling = interaction.client.get_cog("Leveling")  # type: ignore
        leveling_cog.set_enabled_cache(interaction.guild.id, True)
        self.leveling_enable_button.disabled = True
        self.leveling_disable_button.disabled = False
        await interaction.response.edit_message(view=self)

    async def disable_leveling_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if not await self._require_administrator(interaction):
            return
        assert interaction.guild is not None
        updated = await interaction.client.database.edit_leveling_config(guild_id=interaction.guild.id, enabled=False)
        if not updated:
            await interaction.response.send_message("Leveling is not configured for this server.", ephemeral=True)
            return
        leveling_cog: Leveling = interaction.client.get_cog("Leveling")  # type: ignore
        leveling_cog.set_enabled_cache(interaction.guild.id, False)
        self.leveling_enable_button.disabled = False
        self.leveling_disable_button.disabled = True
        await interaction.response.edit_message(view=self)

    @action_row.button(emoji="\N{DIGIT ONE}", style=discord.ButtonStyle.red, disabled=True)
    async def button_one_callback(self, interaction: discord.Interaction[Parrot], button: discord.ui.Button) -> None:
        pass

    @action_row.button(emoji="\N{DIGIT TWO}", style=discord.ButtonStyle.green)
    async def button_two_callback(self, interaction: discord.Interaction[Parrot], button: discord.ui.Button) -> None:
        await interaction.response.send_message("Button two clicked!", ephemeral=True)


class Config(commands.Cog):
    """Cog for managing bot configuration."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

    @commands.group(name="config", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def config(
        self,
        ctx: commands.Context[Parrot],
    ) -> discord.Message:
        """Base command for managing bot configuration.

        This command serves as a parent for various subcommands that allow
        you to configure different aspects of the bot's behavior and settings.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None, "This command can only be used in a server (guild)."

        config = await self.bot.database.get_guild_config(ctx.guild.id)
        if config is None:
            await self.bot.database.register_guild(ctx.guild.id)
            config = await self.bot.database.get_guild_config(ctx.guild.id)

        assert config is not None, "Guild configuration should not be None after registration."

        view = ConfigurationLayout(**config)
        return await ctx.reply(view=view, ephemeral=True)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Config(bot))
