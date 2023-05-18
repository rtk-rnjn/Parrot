from __future__ import annotations

from core import Parrot

from .mod import Moderator


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Moderator(bot))
