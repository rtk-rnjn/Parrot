from __future__ import annotations

from typing import TYPE_CHECKING

from .rtfm import RTFM

if TYPE_CHECKING:
    from core.bot import Parrot


async def setup(bot: Parrot) -> None:
    await bot.add_cog(RTFM(bot))
