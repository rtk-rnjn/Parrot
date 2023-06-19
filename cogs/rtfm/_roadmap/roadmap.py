from __future__ import annotations

import discord
from core import Cog, Context, Parrot
from discord.ext import commands




class Roadmap(Cog):
    """Roadmap.sh scraper. Please visit https://roadmap.sh/ for more information."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
