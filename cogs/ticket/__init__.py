from __future__ import annotations

from core import Parrot
from .ticket import Ticket


def setup(bot: Parrot):
    bot.add_cog(Ticket(bot))
