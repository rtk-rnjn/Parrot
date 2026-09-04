from __future__ import annotations

import asyncio
import logging
import logging.handlers
import os
import socket
from pathlib import Path

from aiohttp import AsyncResolver, ClientSession, TCPConnector
from dotenv import load_dotenv
from rich.logging import RichHandler

from core.bot import Parrot

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FORMAT = "[%(asctime)s] [%(levelname)-8s] [%(name)s] [%(module)s:%(lineno)d:%(funcName)s] - %(message)s"

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

load_dotenv()


def setup_logging() -> None:
    for file in LOG_DIR.glob("*.*"):
        try:
            file.unlink()
        except Exception as e:
            print(f"Failed to delete {file}: {e}")

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
    console_handler.setFormatter(
        logging.Formatter("%(message)s", DATE_FORMAT),
    )

    # Application logs.
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "bot.log",
        mode="w+",
        maxBytes=8 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] [%(levelname)-8s] [%(name)s] - %(message)s",
            DATE_FORMAT,
        ),
    )

    root.addHandler(file_handler)

    # Separate files for third-party loggers.
    separate_loggers = (
        "bot",
        # Discord
        "discord",
        "discord.http",
        # Database / cache
        "pymongo",
        "redis",
    )

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
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] [%(levelname)-8s] [%(name)s] - %(message)s",
                DATE_FORMAT,
            ),
        )

        logger.addHandler(handler)
        logger.addHandler(console_handler)  # Also log to console for convenience.


async def start_bot() -> None:
    _log = logging.getLogger("bot")

    lavalink_process = Parrot.start_lavalink()
    if lavalink_process is not None:
        _log.info("Lavalink process started.")
    else:
        raise SystemExit("Failed to start Lavalink process. Ensure Java is installed and Lavalink.jar is present.")

    bot = Parrot()

    try:
        await bot.database_manager.invalidate_redis()
        async with ClientSession(connector=TCPConnector(resolver=AsyncResolver(), family=socket.AF_INET)) as session:
            async with bot:
                bot._http_session = session
                _log.info("Starting bot.")
                await bot.start()
    except KeyboardInterrupt:
        _log.info("KeyboardInterrupt received. Shutting down.")
    finally:
        await bot.close()
        if lavalink_process is not None:
            lavalink_process.terminate()
            lavalink_process.wait()
        _log.info("Bot has been shut down.")


async def runner():
    setup_logging()

    await asyncio.gather(
        start_bot(),
    )


def main():
    if os.name == "nt":
        # *kiss kiss* to Windows
        asyncio.run(runner(), debug=True)
    else:
        try:
            import uvloop  # noqa: PLC0415

            uvloop.run(runner(), debug=True)
        except ImportError:
            asyncio.run(runner(), debug=True)


if __name__ == "__main__":
    main()
