from __future__ import annotations

from core import Cog, Parrot


class Extra(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_relationship_add(self, relationship):
        pass

    @Cog.listener()
    async def on_relationship_remove(self, relationship):
        pass

    @Cog.listener()
    async def on_relationship_update(self, before, after):
        pass

    @Cog.listener()
    async def on_guild_available(self, guild):
        pass

    @Cog.listener()
    async def on_guild_unavailable(self, guild):
        pass

    @Cog.listener()
    async def on_invite_create(self, invite):
        pass

    @Cog.listener()
    async def on_invite_delete(self, invite):
        pass


def setup(bot):
    bot.add_cog(Extra(bot))
