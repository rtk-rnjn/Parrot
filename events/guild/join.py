from __future__ import annotations

import os
from typing import Any, Dict

import discord
from core import Cog, Parrot

class GuildJoin(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

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
