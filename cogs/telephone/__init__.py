from __future__ import annotations

from core import Parrot
from .telephone import Telephone


def setup(bot: Parrot):
    bot.add_cog(Telephone(bot))
