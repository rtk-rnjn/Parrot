from __future__ import annotations

from core import Parrot

from .giveaway import Giveaways


async def setup(bot: Parrot):
    await bot.add_cog(Giveaways(bot))
