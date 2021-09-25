from __future__ import annotations

from core import Parrot
from .ult import utilities


def setup(bot):
    bot.add_cog(utilities(bot))
