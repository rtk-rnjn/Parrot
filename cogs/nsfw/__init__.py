from __future__ import annotations

from core import Parrot
from .nsfw import NSFW


async def setup(bot: Parrot):
    await bot.add_cog(NSFW(bot))
