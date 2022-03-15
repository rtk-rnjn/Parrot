from __future__ import annotations

from .wolfram import Wolfram
from core import Parrot as Bot


async def setup(bot: Bot) -> None:
    await bot.add_cog(Wolfram(bot))
