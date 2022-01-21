from __future__ import annotations

from discord.ext import ipc

from core import Cog, Parrot


class IpcRoutes(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @ipc.server.route()
    async def get_member_count(self, data):
        guild = self.bot.get_guild(
            data.guild_id
        )  # get the guild object using parsed guild_id

        return guild.member_count  # return the member count to the client
