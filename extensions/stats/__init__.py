from __future__ import annotations

from typing import TYPE_CHECKING

from .cog import StatisticsCog

if TYPE_CHECKING:
    from core import Bot


async def setup(bot: Bot) -> None:
    await bot.add_cog(StatisticsCog(bot))
