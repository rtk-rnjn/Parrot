from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from core import Cog

if TYPE_CHECKING:
    from core import Parrot


class User(Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        pass

    @Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        data = await self.bot.guild_collections_ind.find_one({"_id": guild.id, "sticky_bans": {"$exists": True}})
        if data and user.id in data["sticky_bans"] and guild.me.guild_permissions.ban_members:
            await guild.ban(user, reason="Sticky ban")

    @Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        pass


async def setup(bot: Parrot) -> None:
    await bot.add_cog(User(bot))
