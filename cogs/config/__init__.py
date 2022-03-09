from __future__ import annotations

from .config import Config
from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(Config(bot))
