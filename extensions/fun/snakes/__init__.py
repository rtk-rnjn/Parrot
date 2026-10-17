from __future__ import annotations

from typing import TYPE_CHECKING

from .snakes import Snakes

if TYPE_CHECKING:
    from core import Bot


async def setup(bot: Bot) -> None:
    """Load the cog."""
    await bot.add_cog(Snakes(bot))
