from __future__ import annotations

from core import Parrot, Cog, Context

from .games import Games


def setup(bot: Parrot):
    bot.add_cog(Games(bot))
