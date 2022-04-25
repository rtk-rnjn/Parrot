from __future__ import annotations

from core import Parrot
from .music import Music

async def setup(bot: Parrot):
    await bot.add_cog(Music(bot))