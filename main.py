from __future__ import annotations

import asyncio
import contextlib
import logging
import logging.handlers
import os
import queue
import signal
import socket
from collections import Counter
from pathlib import Path

import aiohttp
import discord
import uvicorn
from aiohttp import AsyncResolver, ClientSession, ClientTimeout, TCPConnector
from dotenv import load_dotenv

from core import Bot
from limited_memory import is_limited_memory
from server import app

load_dotenv()

BOT_NAME = os.getenv("BOT_NAME") or "DiscordBot"
USER_AGENT = os.getenv("BOT_USER_AGENT") or f"{BOT_NAME}/1.0.0 ({os.getenv('GITHUB_REPO')}; {os.getenv('EMAIL_ADDRESS')})"

LIMITED_MEMORY = True

LOGS_ROOT = Path(os.getenv("LOGS_DIR", "logs"))
LOG_FORMAT = "[{asctime}] [{levelname:<8}] {name}:{funcName}:{lineno} - {message}"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class HTTPStats:
    """Counters fed by aiohttp's TraceConfig. Pass ``trace_config()`` to ClientSession."""

    def __init__(self) -> None:
        self.requests = 0
        self.responses = 0
        self.errors = 0
        self.conns_created = 0
        self.conns_reused = 0
        self.conns_queued = 0  # had to wait because the pool limit was hit
        self.status_classes: Counter[str] = Counter()  # "2xx", "4xx", ...

    @property
    def in_flight(self) -> int:
        return max(self.requests - self.responses - self.errors, 0)

    def snapshot(self) -> dict[str, int]:
        return {
            "requests": self.requests,
            "errors": self.errors,
            "created": self.conns_created,
            "reused": self.conns_reused,
            "queued": self.conns_queued,
        }

    def trace_config(self) -> aiohttp.TraceConfig:
        tc = aiohttp.TraceConfig()
        tc.on_request_start.append(self._request_start)
        tc.on_request_end.append(self._request_end)
        tc.on_request_exception.append(self._request_exception)
        tc.on_connection_create_end.append(self._conn_created)
        tc.on_connection_reuseconn.append(self._conn_reused)
        tc.on_connection_queued_end.append(self._conn_queued)
        return tc

    async def _request_start(self, session, ctx, params) -> None:
        self.requests += 1

    async def _request_end(self, session, ctx, params: aiohttp.TraceRequestEndParams) -> None:
        self.responses += 1
        self.status_classes[f"{params.response.status // 100}xx"] += 1

    async def _request_exception(self, session, ctx, params) -> None:
        self.errors += 1

    async def _conn_created(self, session, ctx, params) -> None:
        self.conns_created += 1

    async def _conn_reused(self, session, ctx, params) -> None:
        self.conns_reused += 1

    async def _conn_queued(self, session, ctx, params) -> None:
        self.conns_queued += 1


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
    stop = asyncio.Event()
    install_signal_handlers(stop)

    try:
        timeout = ClientTimeout(total=30, connect=10, sock_connect=10, sock_read=20)
        connector = TCPConnector(resolver=AsyncResolver(), family=socket.AF_INET, ttl_dns_cache=300)
        http_stats = HTTPStats()

        async with (
            ClientSession(
                timeout=timeout,
                connector=connector,
                headers={"User-Agent": USER_AGENT},
                trace_configs=[http_stats.trace_config()],
            ) as session,
            Bot() as bot,
        ):
            bot.set_http_session(session)
            logger.debug("Initializing database connections (Redis & MongoDB)...")

            await bot.database.invalidate_redis()
            await bot.database.ping_mongo_server()
            await bot.database.ping_redis_server()

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

    system_is_limited = is_limited_memory()

    if system_is_limited:
        LIMITED_MEMORY = True
        logger.warning("System has limited memory; enabling LIMITED_MEMORY mode.")
    else:
        LIMITED_MEMORY = False

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
