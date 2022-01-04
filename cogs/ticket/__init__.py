from __future__ import annotations

from core import Parrot
from .ticket import Ticket
from .events import TicketReaction


def setup(bot: Parrot):
    bot.add_cog(Ticket(bot))
    bot.add_cog(TicketReaction(bot))
