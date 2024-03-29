from __future__ import annotations

import discord
from core import Cog, Parrot


class GuildJoin(Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.hook = self.bot._join_leave_log_token

    @Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.wait_until_ready()
        if not guild.chunked:
            await guild.chunk(cache=True)
        content = (
            "```diff\n"
            f"+ Joined {guild.name} ({guild.id})\n"
            f"+ Owner {guild.owner} ({guild.owner.id})\n"
            f"+ {guild.member_count} members\n"
            "\n```"
        )
        if self.hook:
            await self.bot._execute_webhook(self.hook, content=content)

    @Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await self.bot.wait_until_ready()
        content = (
            "```diff\n"
            f"- Left {guild.name} ({guild.id})\n"
            f"- Owner {guild.owner} ({guild.owner.id})\n"
            f"- {guild.member_count} members\n"
            "\n```"
        )
        if self.hook:
            await self.bot._execute_webhook(self.hook, content=content)

    @Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        pass


async def setup(bot: Parrot) -> None:
    await bot.add_cog(GuildJoin(bot))
