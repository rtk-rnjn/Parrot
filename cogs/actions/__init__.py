from __future__ import annotations

from .actions import Actions
from core import Parrot


async def setup(bot: Parrot):
    await bot.add_cog(Actions(bot))
