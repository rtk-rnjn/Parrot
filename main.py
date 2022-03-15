# -*- coding: utf-8 -*-

import asyncio
import socket
from core import Parrot
from aiohttp import AsyncResolver, ClientSession, TCPConnector
from utilities.config import TOKEN

bot = Parrot()

async def main():
    async with ClientSession(connector=TCPConnector(resolver=AsyncResolver(), family=socket.AF_INET)) as http_session:
        async with bot:
            bot.http_session = http_session
            await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
