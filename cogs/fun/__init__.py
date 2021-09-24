from __future__ import annotations

from .fun import fun
from core import Parrot

def setup(bot: Parrot):
  bot.add_cog(fun(bot))