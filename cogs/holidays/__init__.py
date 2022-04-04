from __future__ import annotations

from .pride import Pride
from .hanukkah import Hanukkah
from core import Parrot


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Pride(bot))
    await bot.add_cog(Hanukkah(bot))
