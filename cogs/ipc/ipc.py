from __future__ import annotations
from typing import Any

from core import Parrot, Cog
from discord.ext.ipc import server


class IPCRoutes(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @server.route()
    async def echo(self, data: server.IpcServerResponse) -> Any:
        return data.to_json()
