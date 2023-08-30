from __future__ import annotations

from core import Parrot

from .stats import Stats


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Stats(bot))
