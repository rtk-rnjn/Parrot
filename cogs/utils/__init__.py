from __future__ import annotations

from core import Parrot
from .utils import utils

def setup(bot: Parrot):
    bot.add_cog(utils(bot))