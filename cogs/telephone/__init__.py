from __future__ import annotations

from core import Parrot
from .telephone import Telephone


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Telephone(bot))
