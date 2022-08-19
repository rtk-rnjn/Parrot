# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import socket

from aiohttp import AsyncResolver, ClientSession, TCPConnector  # type: ignore
from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore

from core import Parrot
from utilities.config import TOKEN, my_secret, VERSION

bot: Parrot = Parrot()


async def main() -> None:
    async with ClientSession(
        connector=TCPConnector(resolver=AsyncResolver(), family=socket.AF_INET)
    ) as http_session:
        async with bot:
            bot.http_session = http_session

            if not hasattr(bot, "__version__"):
                bot.__version__ = VERSION

            bot.mongo = AsyncIOMotorClient(
                f"mongodb+srv://user:{my_secret}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority",
            )
            await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
