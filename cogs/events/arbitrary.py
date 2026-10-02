from __future__ import annotations

import logging

import discord
from discord.ext import commands

_log = logging.getLogger("bot.cogs.events.arbitrary")


class ArbitraryEvents(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        _log.info("Cog loaded: %s", self.__class__.__name__)

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
            # I don't know why there is TypeError sometimes, but it happens. I think it's a bug in discord API itself.
            # I did discussed with dpy helpers.
            # Join: discord.gg/dpy
            # https://discord.com/channels/336642139381301249/1153376123443494983/1153376123443494983
            _log.error("Error occurred while processing audit log entry: %s", entry)
            return

        if entry.target and isinstance(entry.target.id, int) and entry.target.id == self.bot.user.id:
            self.bot.dispatch("bot_activity")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ArbitraryEvents(bot))
