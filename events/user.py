from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

import discord
from cogs.meta.robopage import SimplePages
from core import Cog
from discord.ext import commands, tasks

if TYPE_CHECKING:
    from pymongo.collection import Collection

    from core import Context, Parrot


class User(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        pass

    @Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        pass

    @Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        pass


async def setup(bot: Parrot) -> None:
    await bot.add_cog(User(bot))
