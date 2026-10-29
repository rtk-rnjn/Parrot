from __future__ import annotations

import logging

import discord
from discord.ext import commands

_log = logging.getLogger(__name__)


class ArbitraryEvents(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        _log.debug("Cog loaded: %s", self.__class__.__name__)

    @commands.Cog.listener("on_audit_log_entry_create")
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        if self.bot.user is None:
            return

        if entry.user_id and entry.user_id == self.bot.user.id:
            self.bot.dispatch("bot_activity")
            return

        try:
            entry.target  # noqa: B018
        except TypeError:
            # Happens when role is moved or when a channel is moved.
            # Happens on two cases: ROLE_POSITION_UPDATE and CHANNEL_POSITION_UPDATE.
            # In both the cases the target can not be resolved.
            _log.error("Error occurred while processing audit log entry: %s", entry)
            return

        if entry.target and isinstance(entry.target.id, int) and entry.target.id == self.bot.user.id:
            self.bot.dispatch("bot_activity")
