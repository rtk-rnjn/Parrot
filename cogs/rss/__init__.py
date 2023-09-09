from __future__ import annotations

from core import Parrot

from .rss import RSS


async def setup(bot: Parrot) -> None:
    await bot.add_cog(RSS(bot))
