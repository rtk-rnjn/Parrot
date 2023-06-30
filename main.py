# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import logging
import logging.handlers
import os
import socket

from aiohttp import AsyncResolver, ClientSession, TCPConnector
from motor.motor_asyncio import AsyncIOMotorClient

from core import Parrot, CustomFormatter
from utilities.config import DATABASE_KEY, DATABASE_URI, TOKEN, VERSION

bot: Parrot = Parrot()

if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    try:
        import uvloop  # type: ignore

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass

logger = logging.getLogger("discord.http")
logger.setLevel(logging.DEBUG)
filehandler = logging.handlers.RotatingFileHandler(
    filename=".discord-http.log", encoding="utf-8", mode="w", maxBytes=1024, backupCount=5
)
streamhandler = logging.StreamHandler()
filehandler.setFormatter(CustomFormatter())
streamhandler.setFormatter(CustomFormatter())
logger.addHandler(filehandler)
logger.addHandler(streamhandler)


async def main() -> None:
    async with ClientSession(connector=TCPConnector(resolver=AsyncResolver(), family=socket.AF_INET)) as http_session:
        async with bot:
            bot.http_session = http_session

            if not hasattr(bot, "__version__"):
                bot.__version__ = VERSION

            bot.mongo = AsyncIOMotorClient(
                DATABASE_URI.format(DATABASE_KEY),
            )
            bot.init_db()
            await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
