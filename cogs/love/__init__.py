from __future__ import annotations

from core import Parrot

from .love import Love


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Love(bot))
