from __future__ import annotations

from core import Parrot
from .ticket import ticket


def setup(bot: Parrot):
    bot.add_cog(ticket(bot))
