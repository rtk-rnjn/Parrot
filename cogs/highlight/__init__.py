from __future__ import annotations

from .highlight import Highlight
from core import Parrot

async def setup(bot: Parrot) -> None:
    await bot.add_cog(Highlight(bot))