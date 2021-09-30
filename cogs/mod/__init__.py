from __future__ import annotations

from .mod import Mod
from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(Mod(bot))
