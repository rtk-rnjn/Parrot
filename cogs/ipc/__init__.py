from __future__ import annotations

from core import Parrot

from .ipc import IPCRoutes


async def setup(bot: Parrot) -> None:
    await bot.add_cog(IPCRoutes(bot))
