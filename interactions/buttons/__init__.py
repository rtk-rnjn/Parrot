from __future__ import annotations

from core import Parrot, Cog, Context

from .games import Game


def setup(bot: Parrot):
    bot.add_cog(Game(bot))
