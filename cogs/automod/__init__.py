from __future__ import annotations

import re
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .automod import Rule

if TYPE_CHECKING:
    from core.bot import Parrot

VALID_RULE_NAME = re.compile(r"^[a-z0-9_-]{1,32}$", re.IGNORECASE)


class Automod(commands.Cog):
    """Automod rule management."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.rules: dict[int, list[Rule]] = {}

    @commands.group(name="automod", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx: commands.Context[Parrot]) -> None:
        """Shows the help message for the automod feature."""
        # embed = discord.Embed(title="Welcome to Automod")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Automod(bot))
