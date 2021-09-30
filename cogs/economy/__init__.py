from __future__ import annotations

from core import Parrot
from .economy import Economy


def setup(bot: Parrot):
    bot.add_cog(Economy(bot))
