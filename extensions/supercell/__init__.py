from __future__ import annotations

from typing import TYPE_CHECKING

from .brawl_stars import BrawlStars
from .clash_of_clans import ClashOfClans
from .clash_royale import ClashRoyale

if TYPE_CHECKING:
    from core import Bot


async def setup(bot: Bot) -> None:
    await bot.add_cog(ClashOfClans(bot))
    await bot.add_cog(ClashRoyale(bot))
    await bot.add_cog(BrawlStars(bot))
