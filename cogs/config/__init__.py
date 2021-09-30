from __future__ import annotations

from .config import Botconfig
from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(Botconfig(bot))
