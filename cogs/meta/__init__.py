from __future__ import annotations

from core import Parrot
from .meta import meta


def setup(bot: Parrot):
    bot.add_cog(meta(bot))
