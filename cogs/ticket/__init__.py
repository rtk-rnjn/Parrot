from __future__ import annotations

import discord
from discord.ext import commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core import Parrot


class Ticket(commands.Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

