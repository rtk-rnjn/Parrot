from __future__ import annotations

from .config import Configuration
from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(Configuration(bot))
