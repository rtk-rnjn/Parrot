from __future__ import annotations

from .config import BotConfig
from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(BotConfig(bot))
