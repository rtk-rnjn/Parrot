from __future__ import annotations

from core import Parrot

from .ticket import Tickets


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Tickets(bot))
