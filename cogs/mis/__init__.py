from __future__ import annotations

from .mis import Misc
from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(Misc(bot))
