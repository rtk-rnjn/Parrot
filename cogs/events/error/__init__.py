from __future__ import annotations

from typing import TYPE_CHECKING

from .cog import CommandError
from .invocations import CommandLog

if TYPE_CHECKING:
    from core import Parrot

__all__ = ("CommandError", "CommandLog")


async def setup(bot: Parrot) -> None:
    await bot.add_cog(CommandError(bot))
    await bot.add_cog(CommandLog(bot))
