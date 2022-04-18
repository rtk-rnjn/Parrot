from __future__ import annotations

from .api import Gist
from core import Parrot


async def setup(bot: Parrot):
    await bot.add_cog(Gist(bot))
