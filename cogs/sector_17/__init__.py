from __future__ import annotations

from .capture_the_flag import CaptureTheFlag
from core import Parrot

async def setup(bot: Parrot) -> None:
    await bot.add_cog(CaptureTheFlag(bot))