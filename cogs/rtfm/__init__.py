from __future__ import annotations

from .rtfm import RTFM
from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(RTFM(bot))
