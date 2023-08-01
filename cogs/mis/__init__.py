from __future__ import annotations

from core import Parrot

from .mis import Misc
from .listeners import SnipeMessageListener

async def setup(bot: Parrot) -> None:
    await bot.add_cog(Misc(bot))
    await bot.add_cog(SnipeMessageListener(bot))

