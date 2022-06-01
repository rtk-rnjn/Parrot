from __future__ import annotations

from core import Parrot, Cog
from discord.ext.ipc import server


class IPCRoutes(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @server.route()
    async def ping(self, data: server.IpcServerResponse) -> None:
        return data
