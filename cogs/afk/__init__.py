from __future__ import annotations

from core import Parrot

from .afk import AFK


async def setup(bot: Parrot) -> None:
    await bot.add_cog(AFK(bot))
