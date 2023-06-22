from __future__ import annotations

from core import Parrot

from .peggy_playz import PeggyPlayZ
from .sector_17_29 import Sector17Listeners, Sector1729


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Sector1729(bot))
    await bot.add_cog(PeggyPlayZ(bot))
    await bot.add_cog(Sector17Listeners(bot))
