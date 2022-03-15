# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import socket

from aiohttp import AsyncResolver, ClientSession, TCPConnector
import motor.motor_asyncio

from core import Parrot

from utilities.config import TOKEN, my_secret


bot = Parrot()

async def main():
    async with ClientSession(connector=TCPConnector(resolver=AsyncResolver(), family=socket.AF_INET)) as http_session:
        async with bot:
            bot.http_session = http_session
            bot.mongo = motor.motor_asyncio.AsyncIOMotorClient(
                f"mongodb+srv://user:{my_secret}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority", io_loop=bot.loop
            )
            await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
