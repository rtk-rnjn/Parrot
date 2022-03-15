from __future__ import annotations

from .fun import Fun
from core import Parrot


async def setup(bot: Parrot):
    await bot.add_cog(Fun(bot))
