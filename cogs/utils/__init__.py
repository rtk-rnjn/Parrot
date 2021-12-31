from __future__ import annotations

from core import Parrot
from .utils import Utils


def setup(bot: Parrot):
    bot.add_cog(Utils(bot))
