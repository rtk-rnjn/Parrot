from __future__ import annotations

from .method import Easter
from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(Easter(bot))
