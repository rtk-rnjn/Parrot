# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import socket
import os

from aiohttp import AsyncResolver, ClientSession, TCPConnector  # type: ignore
from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore

from core import Parrot
from utilities.config import TOKEN, VERSION, DATABASE_KEY, DATABASE_URI

bot: Parrot = Parrot()

if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main() -> None:
    async with ClientSession(
        connector=TCPConnector(resolver=AsyncResolver(), family=socket.AF_INET)
    ) as http_session:
        async with bot:
            bot.http_session = http_session

            if not hasattr(bot, "__version__"):
                bot.__version__ = VERSION

            bot.mongo = AsyncIOMotorClient(
                DATABASE_URI.format(DATABASE_KEY),
            )
            await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
