from __future__ import annotations

from .fun import Fun
from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(Fun(bot))
