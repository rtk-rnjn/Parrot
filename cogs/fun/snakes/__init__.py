from __future__ import annotations

from typing import TYPE_CHECKING

from .snakes import Snakes

if TYPE_CHECKING:
    from core import Parrot


async def setup(bot: Parrot) -> None:
    """Load the cog."""
    await bot.add_cog(Snakes(bot))
