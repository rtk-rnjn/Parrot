from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from .brawl_stars import BrawlStars
from .clash_of_clans import ClashOfClans
from .clash_royale import ClashRoyale

if TYPE_CHECKING:
    from core import Bot


_log = logging.getLogger(__name__)


async def setup(bot: Bot) -> None:
    capabilities = getattr(bot, "startup_capabilities", {})
    if capabilities.get("Supercell Clash of Clans", bool(os.getenv("SUPERCELL_COC_API"))):
        await bot.add_cog(ClashOfClans(bot))
    else:
        _log.warning("Skipping Clash of Clans cog: API check failed or SUPERCELL_COC_API is missing.")

    if capabilities.get("Supercell Clash Royale", bool(os.getenv("SUPERCELL_ROYALE_API"))):
        await bot.add_cog(ClashRoyale(bot))
    else:
        _log.warning("Skipping Clash Royale cog: API check failed or SUPERCELL_ROYALE_API is missing.")

    if capabilities.get("Supercell Brawl Stars", bool(os.getenv("SUPERCELL_BRAWL_STARS_API"))):
        await bot.add_cog(BrawlStars(bot))
    else:
        _log.warning("Skipping Brawl Stars cog: API check failed or SUPERCELL_BRAWL_STARS_API is missing.")
