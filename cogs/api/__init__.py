from __future__ import annotations

from core import Parrot

from .api import Gist


async def setup(bot: Parrot):
    await bot.add_cog(Gist(bot))
