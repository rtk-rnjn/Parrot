from __future__ import annotations

import asyncio

import discord
from core import Cog, Parrot
from discord.ext import tasks


class ArbitraryEvents(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.bot_activity.start()

        self.FIRST_ON_IDLE_FIRED = False
        self.__retries = 0

    @Cog.listener("on_message")
    async def on_parrot_message(self, message: discord.Message) -> None:
        if message.author.id == self.bot.user.id:
            self.bot.dispatch("bot_activity")

    @Cog.listener("on_message_edit")
    async def on_parrot_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.content != after.content and after.author.id == self.bot.user.id:
            self.bot.dispatch("bot_activity")

    @Cog.listener("on_audit_log_entry_create")
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        if entry.user_id and entry.user_id == self.bot.user.id:
            self.bot.dispatch("bot_activity")

        try:
            entry.target  # noqa: B018
        except TypeError:
            # discord bug or discord.py bug? sometimes entry.target raise TypeError, as id is None
            # actions like, message_pin, message_unpin, members_prune
            return

        if entry.target and (isinstance(entry.target.id, int) and entry.target.id == self.bot.user.id):
            self.bot.dispatch("bot_activity")

    @tasks.loop(seconds=12)
    async def bot_activity(self) -> None:
        try:
            await self.bot.wait_for("bot_activity", timeout=10)
        except asyncio.TimeoutError:
            await self.bot.wait_until_ready()
            self.bot.dispatch("bot_idle")

    async def cog_unload(self) -> None:
        if self.bot_activity.is_running():
            self.bot_activity.cancel()

    @Cog.listener("on_bot_idle")
    async def on_bot_idle(self) -> None:
        for guild in self.bot.guilds:
            if guild.chunked:
                continue
            await self.bot.wait_until_ready()

            while self.__retries < 3:
                try:
                    await guild.chunk(cache=True)
                    break
                except Exception:
                    self.__retries += 1
                    await asyncio.sleep(1)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(ArbitraryEvents(bot))
