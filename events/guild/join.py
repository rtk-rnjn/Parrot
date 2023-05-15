from __future__ import annotations

import os
from typing import Any, Dict

import discord
from core import Cog, Parrot
from utilities.config import WEBHOOK_JOIN_LEAVE_LOGS

HEAD_MODERATOR = 861476968439611392
MODERATOR = 771025632184369152
STAFF = 793531029184708639


class GuildJoin(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.url = WEBHOOK_JOIN_LEAVE_LOGS

    @Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.wait_until_ready()

    @Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await self.bot.wait_until_ready()

    @Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        pass


async def setup(bot: Parrot) -> None:
    await bot.add_cog(GuildJoin(bot))
