from __future__ import annotations

import asyncio
import contextlib
import logging
import logging.handlers
import os
import queue
import signal
import socket
from pathlib import Path

import discord
import uvicorn
from aiohttp import AsyncResolver, ClientSession, ClientTimeout, TCPConnector
from dotenv import load_dotenv

from core import Bot
from server import app

load_dotenv()

BOT_NAME = os.getenv("BOT_NAME") or "DiscordBot"
USER_AGENT = os.getenv("BOT_USER_AGENT") or f"{BOT_NAME}/1.0.0 ({os.getenv('GITHUB_REPO')}; {os.getenv('EMAIL_ADDRESS')})"

LIMITED_MEMORY = os.environ.get("LIMITED_MEMORY", "False").lower() in (
    "true",
    "1",
    "yes",
)

LOGS_ROOT = Path(os.getenv("LOGS_DIR", "logs"))
LOG_FORMAT = "[{asctime}] [{levelname:<8}] {name}:{funcName}:{lineno} - {message}"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class PerModuleFileHandler(logging.Handler):
    """Routes each log record to `logs/<module>/<module>.log` using RotatingFileHandler."""

    def __init__(
        self,
        base_dir: Path = LOGS_ROOT,
        max_bytes: int = 10 * 1024 * 1024,  # 10 MiB per file
        backup_count: int = 5,
    ) -> None:
        super().__init__(level=logging.DEBUG)
        self.base_dir = base_dir
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._handlers: dict[str, logging.handlers.RotatingFileHandler] = {}

    def _resolve_module_name(self, logger_name: str) -> str:
        if not logger_name or logger_name == "root":
            return "root"
        top_level = logger_name.split(".", 1)[0].strip()
        # Sanitize directory/file name
        safe = "".join(ch if (ch.isalnum() or ch in ("_", "-")) else "_" for ch in top_level)
        return safe or "root"

    def _get_handler(self, module_name: str) -> logging.handlers.RotatingFileHandler:
        handler = self._handlers.get(module_name)
        if handler is None:
            module_dir = self.base_dir / module_name
            module_dir.mkdir(parents=True, exist_ok=True)
            log_file = module_dir / f"{module_name}.log"

            handler = logging.handlers.RotatingFileHandler(
                filename=log_file,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            handler.setLevel(logging.DEBUG)
            if self.formatter is not None:
                handler.setFormatter(self.formatter)
            self._handlers[module_name] = handler
        return handler

    def emit(self, record: logging.LogRecord) -> None:
        try:
            module_name = self._resolve_module_name(record.name)
            handler = self._get_handler(module_name)
            handler.emit(record)
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        try:
            for handler in self._handlers.values():
                handler.close()
            self._handlers.clear()
        finally:
            super().close()


@contextlib.contextmanager
def setup_logging(
    logs_dir: Path = LOGS_ROOT,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
):
    """Configure non-blocking console + per-module DEBUG file logging."""
    logs_dir.mkdir(parents=True, exist_ok=True)

    file_formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        style="{",
    )

    per_module_handler = PerModuleFileHandler(base_dir=logs_dir)
    per_module_handler.setLevel(file_level)
    per_module_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    if discord.utils.stream_supports_colour(console_handler.stream):
        console_formatter: logging.Formatter = discord.utils._ColourFormatter()
    else:
        console_formatter = file_formatter
    console_handler.setFormatter(console_formatter)

    # Offload disk and stream I/O from the asyncio event loop onto a listener thread.
    log_queue: queue.SimpleQueue[logging.LogRecord] = queue.SimpleQueue()
    queue_handler = logging.handlers.QueueHandler(log_queue)
    listener = logging.handlers.QueueListener(
        log_queue,
        console_handler,
        per_module_handler,
        respect_handler_level=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    root_logger.addHandler(queue_handler)

    # Ensure key libraries emit DEBUG records and propagate to the root queue handler.
    for logger_name in ("core", "server", "discord", "uvicorn", "uvicorn.error", "uvicorn.access", "aiohttp"):
        mod_logger = logging.getLogger(logger_name)
        mod_logger.setLevel(logging.DEBUG)
        mod_logger.handlers.clear()
        mod_logger.propagate = True

    logging.captureWarnings(True)
    listener.start()
    try:
        yield
    finally:
        listener.stop()
        per_module_handler.close()


logger = logging.getLogger("main")


def install_signal_handlers(stop: asyncio.Event) -> None:
    """Shut down cleanly on SIGINT or SIGTERM; a second signal forces an immediate exit.

    SIGKILL (signal 9) cannot be caught by any process, so nothing can run on it.
    """
    loop = asyncio.get_running_loop()

    def request_shutdown(name: str) -> None:
        if stop.is_set():
            logger.critical("Received second signal (%s); forcing immediate exit.", name)
            os._exit(1)
        logger.info("Received signal %s; initiating graceful shutdown.", name)
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError, RuntimeError):
            loop.add_signal_handler(sig, request_shutdown, sig.name)


async def start_bot() -> None:
    bot = Bot()
    stop = asyncio.Event()
    install_signal_handlers(stop)

    try:
        logger.debug("Initializing database connections (Redis & MongoDB)...")
        await bot.database.invalidate_redis()
        await bot.database.ping_mongo_server()
        await bot.database.ping_redis_server()

        timeout = ClientTimeout(total=30, connect=10, sock_connect=10, sock_read=20)
        connector = TCPConnector(resolver=AsyncResolver(), family=socket.AF_INET, ttl_dns_cache=300)

        async with (
            ClientSession(timeout=timeout, connector=connector, headers={"User-Agent": USER_AGENT}) as session,
            bot,
        ):
            bot.set_http_session(session)
            running = asyncio.create_task(bot.start(), name="Bot: start")
            stopping = asyncio.create_task(stop.wait(), name="Bot: wait for shutdown signal")
            done, _ = await asyncio.wait({running, stopping}, return_when=asyncio.FIRST_COMPLETED)

            stopping.cancel()
            if running in done:
                running.result()
            else:
                logger.info("Closing bot session...")
                await bot.close()
                with contextlib.suppress(asyncio.CancelledError):
                    await running

    except KeyboardInterrupt:
        # Only reached where the loop cannot install signal handlers (Windows).
        logger.info("KeyboardInterrupt received; shutting down bot.")

    except Exception:
        logger.exception("Unhandled exception while running bot.")
        raise

    finally:
        # `async with bot` already closes it after a normal run; this covers failures before that block.
        if not bot.is_closed():
            await bot.close()


async def start_server() -> None:
    config = uvicorn.Config(
        app,
        host="0.0.0.0",  # noqa: S104
        port=8000,
        log_level="debug",
        log_config=None,  # Prevent Uvicorn from overriding root/per-module logging handlers
    )
    server = uvicorn.Server(config)
    await server.serve()


async def runner() -> None:
    logger.info("Starting %s runner...", BOT_NAME)

    start_tasks = [start_bot()]
    if not LIMITED_MEMORY:
        start_tasks.append(start_server())

    await asyncio.gather(*start_tasks)


def main() -> None:
    with setup_logging():
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
