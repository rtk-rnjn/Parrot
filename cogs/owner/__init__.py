from __future__ import annotations

from core import Parrot

from .super_owner import Owner
from .utility import Utility

def setup(bot: Parrot):
    bot.add_cog(Owner(bot))
    bot.add_cog(Utility(bot))
