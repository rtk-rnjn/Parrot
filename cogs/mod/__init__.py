from __future__ import annotations

from .mod import Mod
from .profanity import Profanity
from core import Parrot


def setup(bot: Parrot):
    bot.add_cog(Mod(bot))
    bot.add_cog(Profanity(bot))
    