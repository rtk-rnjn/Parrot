from __future__ import annotations

from core import Parrot
from .hidden import Hidden


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Hidden(bot))