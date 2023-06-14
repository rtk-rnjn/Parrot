from __future__ import annotations

import discord
from core import Cog, Parrot


class OnThread(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.ON_TESTING = False

    @Cog.listener()
    async def on_thread_join(self, thread: discord.Thread) -> None:
        pass

    @Cog.listener()
    async def on_thread_remove(self, thread: discord.Thread) -> None:
        pass

    @Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread) -> None:
        pass

    @Cog.listener()
    async def on_thread_member_join(self, member: discord.ThreadMember) -> None:
        pass

    @Cog.listener()
    async def on_thread_member_remove(self, member: discord.ThreadMember) -> None:
        pass

    @Cog.listener()
    async def on_thread_update(
        self, before: discord.Thread, after: discord.Thread
    ) -> None:
        pass

    @Cog.listener()
    async def on_raw_thread_update(self, payload: discord.RawThreadUpdateEvent) -> None:
        pass

    @Cog.listener()
    async def on_raw_thread_delete(self, payload: discord.RawThreadDeleteEvent) -> None:
        pass

    @Cog.listener()
    async def on_raw_thread_member_remove(
        self, payload: discord.RawThreadMembersUpdate
    ) -> None:
        pass


async def setup(bot: Parrot) -> None:
    await bot.add_cog(OnThread(bot))
