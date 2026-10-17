from __future__ import annotations

import asyncio
import contextlib
import logging
import logging.handlers
import os
import signal
import socket
from pathlib import Path

from aiohttp import AsyncResolver, ClientSession, ClientTimeout, TCPConnector
from dotenv import load_dotenv
from rich.logging import RichHandler

from core import Bot

load_dotenv()

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FORMAT = "[%(asctime)s] [%(levelname)-8s] [%(name)s] [%(module)s:%(lineno)d:%(funcName)s] - %(message)s"

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
BOT_NAME = os.getenv("BOT_NAME") or "DiscordBot"

USER_AGENT = os.getenv("BOT_USER_AGENT") or f"{BOT_NAME}/1.0.0 ({os.getenv('GITHUB_REPO')}; {os.getenv('EMAIL_ADDRESS')})"


def setup_logging() -> None:
    for file in LOG_DIR.glob("*.log"):
        with contextlib.suppress(Exception):
            file.unlink()

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Prevent duplicate handlers.
    root.handlers.clear()

    console_handler = RichHandler(
        level=logging.INFO,
        rich_tracebacks=True,
        show_time=True,
        show_level=True,
        show_path=True,
        markup=True,
        tracebacks_show_locals=False,
    )
    console_handler.setFormatter(logging.Formatter("%(message)s", DATE_FORMAT))

    # Application logs.
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "root.log",
        mode="w+",
        maxBytes=8 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)-8s] [%(name)s] - %(message)s", DATE_FORMAT))

    root.addHandler(file_handler)

    # Separate files for third-party loggers.
    separate_loggers = ("bot", "discord", "discord.http", "pymongo", "redis", "asyncio")

    for name in separate_loggers:
        logger = logging.getLogger(name)

        # Allow DEBUG records to reach the handlers.
        logger.setLevel(logging.DEBUG)

        # Don't send these records to bot.log/root handlers.
        logger.propagate = False

        # Separate file: DEBUG+
        handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / f"{name}.log",
            mode="w+",
            maxBytes=32 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )

        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)-8s] [%(name)s] - %(message)s", DATE_FORMAT))

        logger.addHandler(handler)
        logger.addHandler(console_handler)  # Also log to console for convenience.


def install_signal_handlers(stop: asyncio.Event, log: logging.Logger) -> None:
    """Shut down cleanly on SIGINT or SIGTERM; a second signal forces an immediate exit.

    SIGKILL (signal 9) cannot be caught by any process, so nothing can run on it.
    """
    loop = asyncio.get_running_loop()

    def request_shutdown(name: str) -> None:
        if stop.is_set():
            log.warning("Received %s again, forcing exit.", name)
            os._exit(1)
        log.info("Received %s, shutting down.", name)
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError, RuntimeError):
            loop.add_signal_handler(sig, request_shutdown, sig.name)


async def start_bot() -> None:
    _log = logging.getLogger(__name__)

    bot = Bot()
    stop = asyncio.Event()
    install_signal_handlers(stop, _log)

    try:
        await bot.database.invalidate_redis()
        await bot.database.ping_mongo_server()
        await bot.database.ping_redis_server()

        timeout = ClientTimeout(total=30, connect=10, sock_connect=10, sock_read=20)
        connector = TCPConnector(resolver=AsyncResolver(), family=socket.AF_INET, ttl_dns_cache=300)

        async with ClientSession(timeout=timeout, connector=connector, headers={"User-Agent": USER_AGENT}) as session, bot:
            bot.set_http_session(session)
            _log.info("Starting bot.")
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
        _log.info("KeyboardInterrupt received. Shutting down.")

    finally:
        # `async with bot` already closes it after a normal run; this covers failures before that block.
        if not bot.is_closed():
            await bot.close()
        _log.info("Bot has been shut down.")


async def runner():
    setup_logging()

    await asyncio.gather(start_bot())


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
