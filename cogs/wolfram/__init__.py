from __future__ import annotations

from core import Parrot as Bot

from .wolfram import Wolfram


async def setup(bot: Bot) -> None:
    await bot.add_cog(Wolfram(bot))
