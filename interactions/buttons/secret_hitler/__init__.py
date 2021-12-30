from __future__ import annotations

import discord
from discord.ext import commands
from discord.utils import MISSING
from core import Parrot, Cog, Context

from .game import *
from .ui import *


class SecretHitler(Cog):
    def __init__(self, bot: Parrot) -> None:
        super().__init__(bot)
        self.games: dict[int, discord.ui.View] = {}

    @commands.guild_only()
    @commands.command(aliases=["umbrogus"])
    async def secret_hitler(self, ctx: Context) -> None:
        if ctx.channel.id in self.games:
            raise commands.BadArgument("There is already a game running in this channel.")

        self.games[ctx.channel.id] = MISSING
        await JoinUI.start(ctx, self.games)


def setup(bot: Parrot) -> None:
    bot.add_cog(SecretHitler(bot))