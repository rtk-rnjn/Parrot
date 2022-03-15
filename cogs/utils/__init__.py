from __future__ import annotations

from core import Parrot
from .utils import Utils


async def setup(bot: Parrot):
    await bot.add_cog(Utils(bot))
