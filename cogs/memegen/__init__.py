from __future__ import annotations

from core import Parrot
from .memegen import Memegen


async def setup(bot: Parrot):
    await bot.add_cog(Memegen(bot))
