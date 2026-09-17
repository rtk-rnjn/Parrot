from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from core.utils import PaginationLayout

from .utils import (
    BirthdayChannelSelect,
    ChangeBotPrefixButton,
    GiveawayEditButton,
    HubChannelSelect,
    LevelingChannelSelect,
    MuteRoleSelect,
    StarboardEditButton,
    TelephoneChannelSelect,
    WelcomeEditButton,
)

if TYPE_CHECKING:
    from core import Parrot


_log = logging.getLogger("bot.cogs.config")

EVENTS_DESCRIPTIONS = {
    "on_member_join": "Triggered when a member joins the server.",
    "on_member_leave": "Triggered when a member leaves the server.",
    "on_member_ban": "Triggered when a member is banned from the server.",
    "on_member_unban": "Triggered when a member is unbanned from the server.",
    "on_message_delete": "Triggered when a message is deleted.",
    "on_message_edit": "Triggered when a message is edited.",
    "on_channel_delete": "Triggered when a channel is deleted.",
    "on_channel_create": "Triggered when a channel is created.",
    "on_channel_update": "Triggered when a channel is updated.",
    "on_thread_create": "Triggered when a thread is created.",
    "on_thread_delete": "Triggered when a thread is deleted.",
    "on_thread_update": "Triggered when a thread is updated.",
    "on_server_update": "Triggered when the server is updated.",
    "on_webhook_update": "Triggered when a webhook is updated.",
    "on_role_create": "Triggered when a role is created.",
    "on_role_delete": "Triggered when a role is deleted.",
    "on_role_update": "Triggered when a role is updated.",
    "on_member_join_voice": "Triggered when a member joins a voice channel.",
    "on_member_leave_voice": "Triggered when a member leaves a voice channel.",
    "on_member_move_voice": "Triggered when a member moves between voice channels.",
}


COMMAND_PREFIX_DESCRIPTION = """
## Command Prefix
-# Change the bot's command prefix. The command prefix is used to invoke commands in the server. Prefix based command will be obsolete in the future, so it's recommended to use slash commands instead.
"""

MUTE_ROLE_DESCRIPTION = """
## Mute Role
-# Select a role to be used as the mute role for the server. This role should have the "Send Messages" and "Connect" permissions disabled in all channels where you want to mute members.
"""

HUB_CHANNEL_DESCRIPTION = """
## Hub Channel
-# Select a channel to be used as the hub channel for the server. Basically Join to create voice channel. If a user joins the hub channel, a new voice channel will be created for them. When they leave, the channel will be deleted.
"""

BIRTHDAY_CHANNEL_DESCRIPTION = """
## Birthday Channel
-# Select a channel to be used for birthday announcements. The bot will announce birthdays in this channel.
"""

TELEPHONE_CHANNEL_DESCRIPTION = """
## Telephone Channel
-# Select a channel to be used for the telephone feature. Server members can chat with other members of different servers. If no channel is selected other servers won't be able to chat with your server members.
"""

LEVELING_CHANNEL_DESCRIPTION = """
## Leveling Channel
-# Select a channel to be used for leveling announcements. The bot will announce when a member levels up in this channel.
"""

WELCOME_CONFIG_DESCRIPTION = """
## Welcome Configuration
-# Configure the welcome settings for the server. You can set a welcome message, a channel for welcome messages, and a role to be assigned to new members and even leave messages for when members leave the server.
"""

GIVEAWAY_CONFIG_DESCRIPTION = """
## Giveaway Configuration
-# Configure the giveaway settings for the server. You can set a channel for giveaways and a role to be mentioned when giveaways are announced.
"""

STARBOARD_CONFIG_DESCRIPTION = """
## Starboard Configuration
-# Configure the starboard settings for the server. You can set a channel for the starboard, the threshold for messages to be posted to the starboard, and the emoji used for starboard reactions.
"""


class Config(commands.Cog):
    """Cog for managing bot configuration."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

    @commands.group(name="config", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def config(self, ctx: commands.Context[Parrot]) -> discord.Message:
        """Base command for managing bot configuration.

        This command serves as a parent for various subcommands that allow
        you to configure different aspects of the bot's behavior and settings.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None, "This command can only be used in a server (guild)."

        config = await self.bot.database.get_guild_configuration(ctx.guild.id)
        if config is None:
            await self.bot.database.register_guild(ctx.guild.id)
            config = await self.bot.database.get_guild_configuration(ctx.guild.id)

        assert config is not None, "Guild configuration should not be None after registration."

        header = discord.ui.TextDisplay(
            "# Bot Configuration\n-# Parrot Bot is highly customizable. Use the buttons below to navigate through the configuration options.",
        )
        footer = discord.ui.TextDisplay("-# Use buttons to navigate through the pages.")

        view = PaginationLayout(
            ctx.author,
            header=header,
            items=[
                [
                    discord.ui.Section(
                        discord.ui.TextDisplay(COMMAND_PREFIX_DESCRIPTION),
                        accessory=ChangeBotPrefixButton(bot_prefix=config.get("command_prefix", self.bot.DEFAULT_PREFIX)),
                    ),
                    discord.ui.Separator(),
                    discord.ui.TextDisplay(MUTE_ROLE_DESCRIPTION),
                    discord.ui.ActionRow(MuteRoleSelect(mute_role_id=config["mute_role_id"])),
                    discord.ui.Separator(),
                    discord.ui.TextDisplay(HUB_CHANNEL_DESCRIPTION),
                    discord.ui.ActionRow(HubChannelSelect(hub_channel_id=config["hub_channel_id"])),
                    discord.ui.Separator(),
                    discord.ui.TextDisplay(BIRTHDAY_CHANNEL_DESCRIPTION),
                    discord.ui.ActionRow(BirthdayChannelSelect(hub_channel_id=config["birthday_config"]["channel_id"])),
                    discord.ui.Separator(),
                    discord.ui.TextDisplay(TELEPHONE_CHANNEL_DESCRIPTION),
                    discord.ui.ActionRow(TelephoneChannelSelect(hub_channel_id=config["telephone_config"]["channel_id"])),
                    discord.ui.Separator(),
                    discord.ui.TextDisplay(LEVELING_CHANNEL_DESCRIPTION),
                    discord.ui.ActionRow(LevelingChannelSelect(leveling_channel_id=config["leveling_config"]["channel_id"])),
                ],
                [
                    discord.ui.Section(
                        discord.ui.TextDisplay(WELCOME_CONFIG_DESCRIPTION),
                        accessory=WelcomeEditButton(**config),
                    ),
                    discord.ui.Separator(),
                    discord.ui.Section(
                        discord.ui.TextDisplay(GIVEAWAY_CONFIG_DESCRIPTION),
                        accessory=GiveawayEditButton(**config),
                    ),
                    discord.ui.Separator(),
                    discord.ui.Section(
                        discord.ui.TextDisplay(STARBOARD_CONFIG_DESCRIPTION),
                        accessory=StarboardEditButton(**config),
                    ),
                ],
            ],
            footer=footer,
        )

        return await ctx.reply(view=view, ephemeral=True)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Config(bot))
