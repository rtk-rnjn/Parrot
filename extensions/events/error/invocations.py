from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)


class CommandLog(commands.Cog, command_attrs={"hidden": True}):
    """This category is of no use for you, ignore it."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context[Bot]) -> None:
        if ctx.author.bot or ctx.guild is None or ctx.command is None:
            return

        _log.debug(
            "Command invoked: %s",
            {
                "command": ctx.command.qualified_name,
                "author_id": ctx.author.id,
                "message_id": ctx.message.id,
                "channel_id": ctx.channel.id,
                "guild_id": ctx.guild.id,
                "message_content": ctx.message.content,
                "is_command_failed": ctx.command_failed,
            },
        )
