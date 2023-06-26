from __future__ import annotations

from core import Parrot

from .listener import OwnerListener
from .owner import DiscordPy, Owner


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Owner(bot))
    await bot.add_cog(DiscordPy(bot))
    await bot.add_cog(OwnerListener(bot))
