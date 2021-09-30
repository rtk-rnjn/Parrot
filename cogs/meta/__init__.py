from __future__ import annotations

from core import Parrot
from .meta import Meta


def setup(bot: Parrot):
    bot.add_cog(Meta(bot))
