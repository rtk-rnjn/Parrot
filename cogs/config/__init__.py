from __future__ import annotations

from core import Parrot

from .config import Configuration


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Configuration(bot))
