from __future__ import annotations

from core import Parrot
from .nasa import NASA


def setup(bot: Parrot):
    bot.add_cog(NASA(bot))
