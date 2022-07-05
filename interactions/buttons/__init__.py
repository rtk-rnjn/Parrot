from __future__ import annotations

from core import Parrot

from .games import Games


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Games(bot))
