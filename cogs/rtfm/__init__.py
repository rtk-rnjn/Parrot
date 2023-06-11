from __future__ import annotations

from core import Parrot

from .linter import Linter
from .rtfm import RTFM


async def setup(bot: Parrot) -> None:
    await bot.add_cog(RTFM(bot))
    await bot.add_cog(Linter(bot))
