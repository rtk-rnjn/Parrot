from __future__ import annotations

from core import Parrot
from .nasa import nasa


def setup(bot: Parrot):
    bot.add_cog(nasa(bot))
