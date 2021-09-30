from __future__ import annotations

from core import Parrot
from .nsfw import NSFW


def setup(bot: Parrot):
    bot.add_cog(NSFW(bot))
