from __future__ import annotations

from core import Parrot

from .super_owner import Owner, DiscordPy


def setup(bot: Parrot):
    bot.add_cog(Owner(bot))
    bot.add_cog(DiscordPy(bot))
