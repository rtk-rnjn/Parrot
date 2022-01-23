from __future__ import annotations

from .pride import Pride
from .hanukkah import Hanukkah
from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(Pride(bot))
    bot.add_cog(Hanukkah(bot))
