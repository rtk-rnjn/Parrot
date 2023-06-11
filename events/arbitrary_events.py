from __future__ import annotations

import asyncio

import discord
from core import Cog, Context, Parrot
from discord.ext import tasks


class ArbitraryEvents(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.bot_activity.start()

    @Cog.listener("on_socket_raw_send")
    async def on_socket_raw_send(self, payload: str) -> None:
        self.bot.dispatch("bot_activity")

    @tasks.loop(count=1)
    async def bot_activity(self) -> None:
        try:
            await self.bot.wait_for("bot_activity", timeout=10)
        except asyncio.TimeoutError:
            self.bot.dispatch("bot_idle")

        else:
            self.bot_activity.restart()

    async def cog_unload(self) -> None:
        if self.bot_activity.is_running():
            self.bot_activity.cancel()
