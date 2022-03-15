from __future__ import annotations

from .config import Configuration
from core import Parrot


async def setup(bot: Parrot):
    await bot.add_cog(Configuration(bot))
