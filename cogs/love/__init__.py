from __future__ import annotations

from core import Parrot
from .love import Love


def setup(bot: Parrot):
    bot.add_cog(Love(bot))
