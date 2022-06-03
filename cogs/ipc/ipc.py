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

    @server.route()
    async def db_exec_find_one(self, data: server.IpcServerResponse) -> Any:
        db = data.db
        collection = data.collection
        query = data.query
        projection = data.projection

        return await self.bot.mongo[db][collection].find_one(query, projection)

    @server.route()
    async def db_exec_update_one(self, data: server.IpcServerResponse) -> Any:
        db = data.db
        collection = data.collection
        query = data.query
        update = data.update
        upsert = data.upsert

        return await self.bot.mongo[db][collection].update_one(query, update, upsert=upsert)
    