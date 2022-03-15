from __future__ import annotations

from core import Parrot
from ._snakes_cog import Snakes


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Snakes(bot))
