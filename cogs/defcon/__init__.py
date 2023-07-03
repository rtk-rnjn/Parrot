from __future__ import annotations

from core import Parrot

from .defcon import Defcon
from .events import DefconListeners


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Defcon(bot))
    await bot.add_cog(DefconListeners(bot))
