from __future__ import annotations

import io
import json
from contextlib import suppress
from typing import List, Sequence, Tuple, Union

import discord
from core import Cog, Parrot


class GuildRoleEmoji(Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        pass

    @Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        pass

    @Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        pass

    @Cog.listener()
    async def on_guild_emojis_update(
        self,
        guild: discord.Guild,
        before: Sequence[discord.Emoji],
        after: Sequence[discord.Emoji],
    ):
        pass


async def setup(bot: Parrot) -> None:
    await bot.add_cog(GuildRoleEmoji(bot))
