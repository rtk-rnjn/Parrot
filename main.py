from __future__ import annotations

import asyncio
import contextlib
import os
import socket

import aioredis
from aiohttp import AsyncResolver, ClientSession, TCPConnector
from motor.motor_asyncio import AsyncIOMotorClient

from app import runner
from core import Parrot
from updater import init
from utilities.config import DATABASE_KEY, DATABASE_URI, MINIMAL_BOOT, REDIS_URI, TOKEN, VERSION

bot: Parrot = Parrot()

if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    with contextlib.suppress(ImportError):
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


async def main() -> None:
    async with ClientSession(connector=TCPConnector(resolver=AsyncResolver(), family=socket.AF_INET)) as http_session:
        async with bot:
            bot.http_session = http_session
            bot.sql = await init()

            if not hasattr(bot, "__version__"):
                bot.__version__ = VERSION

            bot.mongo = AsyncIOMotorClient(DATABASE_URI.format(DATABASE_KEY))  # type: ignore
            redis = await aioredis.from_url(REDIS_URI, encoding="utf-8", decode_responses=True, max_connections=1000)
            bot.redis = redis

            await bot.init_db()

            start_what = [bot.start(TOKEN)]

            if not MINIMAL_BOOT:
                start_what.append(runner())

            await asyncio.gather(*start_what)


if __name__ == "__main__":
    asyncio.run(main())
