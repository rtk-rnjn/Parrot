from __future__ import annotations

from .sector_17_29 import Sector1729
from .peggy_playz import PeggyPlayZ

from core import Parrot


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Sector1729(bot))
    await bot.add_cog(PeggyPlayZ(bot))
