from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core import Bot


class GuildEventListener(commands.Cog):
    """A cog that listens for guild events and updates the database accordingly."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Called when the bot joins a new guild."""
        await self.bot.database.register_guild(guild.id)

    @commands.Cog.listener()
    async def on_guild_available(self, guild: discord.Guild) -> None:
        """Called when a guild becomes available."""
        await self.bot.database.register_guild(guild.id)
