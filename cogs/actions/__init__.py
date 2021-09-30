from __future__ import annotations

from .actions import Actions
from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(Actions(bot))
