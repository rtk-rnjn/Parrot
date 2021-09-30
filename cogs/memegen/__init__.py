from __future__ import annotations

from core import Parrot
from .memegen import Memegen


def setup(bot: Parrot):
    bot.add_cog(Memegen(bot))
