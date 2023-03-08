from __future__ import annotations

from core import Parrot

from .jsk import MongoFeature

async def setup(bot: Parrot):
    bot.add_cog(MongoFeature(bot=bot))