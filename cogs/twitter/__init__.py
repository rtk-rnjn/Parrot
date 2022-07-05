from __future__ import annotations

from core import Parrot

from .twitter import Twitter


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Twitter(bot))
