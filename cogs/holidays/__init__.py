from __future__ import annotations

from core import Parrot

from .hanukkah import Hanukkah
from .pride import Pride


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Pride(bot))
    await bot.add_cog(Hanukkah(bot))
