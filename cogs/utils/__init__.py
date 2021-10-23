from __future__ import annotations

from core import Parrot
from .utils import Utils
from .timers import Timer

def setup(bot: Parrot):
    bot.add_cog(Utils(bot))
    bot.add_cog(Timer(bot))