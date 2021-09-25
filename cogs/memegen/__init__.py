from __future__ import annotations

from core import Parrot
from .memegen import memegen


def setup(bot: Parrot):
    bot.add_cog(memegen(bot))
