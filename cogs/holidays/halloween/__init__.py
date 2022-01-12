from __future__ import annotations

from .method import Halloween
from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(Halloween(bot))
