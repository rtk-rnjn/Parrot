from __future__ import annotations

from core import Parrot

from .super_owner import owner, discordpy


def setup(bot: Parrot):
    bot.add_cog(owner(bot))
    bot.add_cog(discordpy(bot))
