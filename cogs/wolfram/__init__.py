from __future__ import annotations

from .wolfram import Wolfram
from core import Parrot as Bot


def setup(bot: Bot) -> None:
    bot.add_cog(Wolfram(bot))
