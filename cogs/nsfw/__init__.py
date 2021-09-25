from __future__ import annotations

from core import Parrot
from .nsfw import nsfw


def setup(bot: Parrot):
    bot.add_cog(nsfw(bot))
