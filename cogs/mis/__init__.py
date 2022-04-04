from __future__ import annotations

from .mis import Misc
from core import Parrot


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Misc(bot))
