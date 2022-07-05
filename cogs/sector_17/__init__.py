from __future__ import annotations

from core import Parrot

from .sector_17 import Sector1729


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Sector1729(bot))
