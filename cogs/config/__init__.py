from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

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
        return await ctx.reply(str(config))



async def setup(bot: Parrot) -> None:
    await bot.add_cog(Config(bot))
