from __future__ import annotations

from core import Parrot

from .super_owner import DiscordPy, Owner


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Owner(bot))
    await bot.add_cog(DiscordPy(bot))
