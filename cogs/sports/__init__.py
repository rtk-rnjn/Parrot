from __future__ import annotations

from core import Parrot

from .sports import Sports


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Sports(bot))
