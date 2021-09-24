from __future__ import annotations
from core import Cog, Parrot

class User(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_member_ban(self, guild, user):
        pass

    @Cog.listener()
    async def on_member_unban(self, guild, user):
        pass

    @Cog.listener()
    async def on_user_update(self, before, after):
        pass


def setup(bot):
    bot.add_cog(User(bot))
