from __future__ import annotations

from .fun import Fun
# from .one_word_story import OneWordStory
# from .counting import Counting

from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(Fun(bot))
    # bot.add_cog(OneWordStory(bot))
    # bot.add_cog(Counting(bot))
