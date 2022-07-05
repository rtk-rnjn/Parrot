from __future__ import annotations

from core import Parrot

from .fun import Fun


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Fun(bot))
