from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Parrot

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

        await interaction.client.database_manager.set_command_prefix(
            guild_id=interaction.guild.id,
            command_prefix=new_prefix,
        )

        await interaction.followup.send(
            f"You submitted a new bot prefix: `{new_prefix}`. This is where you would implement the logic to update the bot's prefix in your configuration.",
            ephemeral=True,
        )


class ConfigurationLayout(discord.ui.LayoutView):
    def __init__(
        self,
        *,
        bot_prefix: str,
        mute_role: discord.Role | None,
        roles: list[discord.Role] | None = None,
    ) -> None:
        super().__init__()

        self.bot_prefix = bot_prefix

        prefix_section_button = discord.ui.Button(label=self.bot_prefix, style=discord.ButtonStyle.green)
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

        container = discord.ui.Container(
            discord.ui.TextDisplay(
                "## Configuration\n-# This is the configuration panel for the bot. You can change various settings here.\n",
            ),
            discord.ui.Separator(),
            prefix_section,
            discord.ui.Separator(),
            mute_role_section,
            mute_role_selector,
        )

        self.add_item(container)

    async def change_prefix_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        await interaction.response.send_modal(UpdateBotPrefixModal(bot_prefix=self.bot_prefix))

    async def delete_mute_role_callback(self, interaction: discord.Interaction[Parrot]) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server (guild).",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        await interaction.client.database_manager.delete_mute_role(guild_id=interaction.guild.id)
        await interaction.client.timer_manager.delete_timer(event_name="mute", metadata_filter={"guild_id": interaction.guild.id}, multiple=True)

        await interaction.followup.send(
            "The mute role has been deleted. Users will no longer be muted until a new mute role is set.",
            ephemeral=True,
        )


class Config(commands.Cog):
    """Cog for managing bot configuration."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

    @commands.command(name="config")
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

        prefix = await self.bot.database_manager.get_command_prefix(guild_id=ctx.guild.id)
        mute_role_id = await self.bot.database_manager.get_guild_mute_role(guild_id=ctx.guild.id)

        view = ConfigurationLayout(
            bot_prefix=prefix or ctx.bot.DEFAULT_PREFIX,
            mute_role=ctx.guild.get_role(mute_role_id) if mute_role_id else None,
        )
        return await ctx.reply(view=view, ephemeral=True)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Config(bot))
