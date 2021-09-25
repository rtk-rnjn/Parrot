from __future__ import annotations
from core import Cog, Parrot


class PrivateChannel(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_private_channel_delete(self, channel):
        pass

    @Cog.listener()
    async def on_private_channel_create(self, channel):
        pass

    @Cog.listener()
    async def on_private_channel_update(self, before, after):
        pass

    @Cog.listener()
    async def on_private_channel_pins_update(self, channel, last_pin):
        pass

    @Cog.listener()
    async def on_group_join(self, channel, user):
        pass

    @Cog.listener()
    async def on_group_remove(self, channel, user):
        pass


def setup(bot):
    bot.add_cog(PrivateChannel(bot))
