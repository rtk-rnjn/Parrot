from __future__ import annotations

import discord
from core import Cog, Parrot


class Extra(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_guild_available(self, guild: discord.Guild):
        pass

    @Cog.listener()
    async def on_guild_unavailable(self, guild: discord.Guild):
        pass

    @Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        pass

    @Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        pass


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Extra(bot))
