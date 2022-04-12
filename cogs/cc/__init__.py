from __future__ import annotations

from .cc import CustomCommand
from core import Parrot


async def setup(bot: Parrot) -> None:
    await bot.add_cog(CustomCommand(bot))
