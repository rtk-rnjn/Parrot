from __future__ import annotations

from .music import Music
from core import Parrot


async def setup(bot: Parrot):
    await bot.add_cog(Music(bot))
