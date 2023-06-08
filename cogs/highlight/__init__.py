from __future__ import annotations

from core import Parrot

from .highlight import Highlight


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Highlight(bot))
