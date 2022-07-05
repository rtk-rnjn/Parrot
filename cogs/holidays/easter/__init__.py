from __future__ import annotations

from core import Parrot

from .easter import Easter


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Easter(bot))
