from __future__ import annotations

from core import Parrot
from .nasa import NASA


async def setup(bot: Parrot) -> None:
    await bot.add_cog(NASA(bot))
