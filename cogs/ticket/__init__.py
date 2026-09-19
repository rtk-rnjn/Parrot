from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core import Parrot


class Ticket(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Ticket(bot))
