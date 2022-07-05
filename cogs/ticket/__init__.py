from __future__ import annotations

from core import Parrot

from .events import TicketReaction
from .ticket import Ticket


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Ticket(bot))
    await bot.add_cog(TicketReaction(bot))
