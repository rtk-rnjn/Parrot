from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import socket

import uvicorn
from aiohttp import AsyncResolver, ClientSession, ClientTimeout, TCPConnector
from dotenv import load_dotenv

from core import Bot
from server import app

load_dotenv()


BOT_NAME = os.getenv("BOT_NAME") or "DiscordBot"

USER_AGENT = os.getenv("BOT_USER_AGENT") or f"{BOT_NAME}/1.0.0 ({os.getenv('GITHUB_REPO')}; {os.getenv('EMAIL_ADDRESS')})"


def install_signal_handlers(stop: asyncio.Event) -> None:
    """Shut down cleanly on SIGINT or SIGTERM; a second signal forces an immediate exit.

    SIGKILL (signal 9) cannot be caught by any process, so nothing can run on it.
    """
    loop = asyncio.get_running_loop()

    def request_shutdown(name: str) -> None:
        if stop.is_set():
            os._exit(1)
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError, RuntimeError):
            loop.add_signal_handler(sig, request_shutdown, sig.name)


async def start_bot() -> None:

    bot = Bot()
    stop = asyncio.Event()
    install_signal_handlers(stop)

    try:
        await bot.database.invalidate_redis()
        await bot.database.ping_mongo_server()
        await bot.database.ping_redis_server()

        timeout = ClientTimeout(total=30, connect=10, sock_connect=10, sock_read=20)
        connector = TCPConnector(resolver=AsyncResolver(), family=socket.AF_INET, ttl_dns_cache=300)

        async with ClientSession(timeout=timeout, connector=connector, headers={"User-Agent": USER_AGENT}) as session, bot:
            bot.set_http_session(session)
            running = asyncio.create_task(bot.start(), name="Bot: start")
            stopping = asyncio.create_task(stop.wait(), name="Bot: wait for shutdown signal")
            done, _ = await asyncio.wait({running, stopping}, return_when=asyncio.FIRST_COMPLETED)

            stopping.cancel()
            if running in done:
                running.result()
            else:
                await bot.close()
                with contextlib.suppress(asyncio.CancelledError):
                    await running

    except KeyboardInterrupt:
        # Only reached where the loop cannot install signal handlers (Windows).
        pass

    finally:
        # `async with bot` already closes it after a normal run; this covers failures before that block.
        if not bot.is_closed():
            await bot.close()


async def start_server() -> None:
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")  # noqa: S104
    server = uvicorn.Server(config)
    await server.serve()


async def runner():
    await asyncio.gather(start_bot(), start_server())


def main():
    if os.name == "nt":
        # *kiss kiss* to Windows
        asyncio.run(runner())
    else:
        try:
            import uvloop  # noqa: PLC0415

            uvloop.run(runner())
        except ImportError:
            asyncio.run(runner())


if __name__ == "__main__":
    main()
