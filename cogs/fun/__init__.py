from __future__ import annotations

from .fun import Fun

# from .one_word_story import OneWordStory
# from .counting import Counting

from core import Parrot


async def setup(bot: Parrot):
    await bot.add_cog(Fun(bot))
    # await bot.add_cog(OneWordStory(bot))
    # await bot.add_cog(Counting(bot))
