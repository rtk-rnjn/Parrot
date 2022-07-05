from __future__ import annotations

from core import Parrot

from .meta import Meta


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Meta(bot))
