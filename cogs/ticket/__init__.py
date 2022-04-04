from __future__ import annotations

from core import Parrot
from .ticket import Ticket
from .events import TicketReaction


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Ticket(bot))
    await bot.add_cog(TicketReaction(bot))
