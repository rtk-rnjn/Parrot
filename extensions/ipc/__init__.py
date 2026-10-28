from __future__ import annotations

import asyncio
import inspect
import json
import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands, tasks

if TYPE_CHECKING:
    from core import Bot


log = logging.getLogger(__name__)

IPC_REQUEST_CHANNEL = "parrot:ipc:request"
IPC_EVENTS_CHANNEL = "parrot:ipc:events"
IPC_RESPONSE_PREFIX = "parrot:ipc:response"
TELEMETRY_KEY = "parrot:telemetry:status"
TELEMETRY_INTERVAL_SEC = 15.0
TELEMETRY_TTL_SEC = 60
MAX_DETAIL_CHANNELS = 25


def ipc_op(name: str):
    """Mark a cog method as the handler for IPC operation `name`."""

    def decorator(func: Callable[[Any, Mapping[str, Any]], Awaitable[Mapping[str, Any]]]) -> Callable:
        func.__ipc_operation__ = name
        return func

    return decorator


@dataclass(slots=True)
class IPCRequest:
    corr_id: str
    op: str
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, raw_data: str | bytes) -> IPCRequest | None:
        """Return a valid request, or None if the message is malformed."""
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError, UnicodeDecodeError:
            return None

        if not isinstance(data, dict):
            return None

        corr_id, op = data.get("corr_id"), data.get("op")
        if not corr_id or not op:
            return None

        return cls(corr_id=corr_id, op=op, payload=data.get("payload") or {})

    @property
    def response_channel(self) -> str:
        return f"{IPC_RESPONSE_PREFIX}:{self.corr_id}"


def parse_int(value: str | int | None) -> int | None:
    if value is None:
        return None

    if isinstance(value, int):
        return value

    try:
        return int(value)
    except TypeError, ValueError:
        return None


def require_int(payload: Mapping[str, Any], key: str) -> int:
    value = parse_int(payload.get(key))
    if value is None:
        message = f"Missing or invalid '{key}' in payload: {payload}"
        raise ValueError(message)
    return value


def elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


class ParrotRedisIPC(commands.Cog):
    """Redis Pub/Sub Inter-Process Communication Cog for Parrot Bot."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.redis = bot.database.redis_client
        self.pubsub = None
        self.started_at = time.time()
        self._listener_task: asyncio.Task[None] | None = None
        self._pending: set[asyncio.Task[None]] = set()
        self._handlers = self._collect_handlers()

    async def cog_load(self) -> None:
        await self._subscribe()
        self._start_listener()
        self.publish_telemetry.start()
        log.info("ParrotRedisIPC subscribed to %s", IPC_REQUEST_CHANNEL)

    async def cog_unload(self) -> None:
        self.publish_telemetry.cancel()
        self._stop_listener()
        self._cancel_pending()
        await self._unsubscribe()

    async def _subscribe(self) -> None:
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(IPC_REQUEST_CHANNEL)

    async def _unsubscribe(self) -> None:
        if not self.pubsub:
            return
        await self.pubsub.unsubscribe(IPC_REQUEST_CHANNEL)

    def _start_listener(self) -> None:
        self._listener_task = asyncio.create_task(self._listen_loop(), name="parrot-redis-ipc")

    def _stop_listener(self) -> None:
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()

    def _cancel_pending(self) -> None:
        for task in self._pending:
            task.cancel()

    def _collect_handlers(self):
        return {
            name: method
            for name, method in inspect.getmembers(self, predicate=inspect.iscoroutinefunction)
            if getattr(method, "__ipc_operation__", None) is not None
        }

    def _get_handler(self, op: str):
        handler = self._handlers.get(op)
        if handler is None:
            message = f"Unsupported IPC operation: {op}"
            raise ValueError(message)
        return handler

    @tasks.loop(seconds=TELEMETRY_INTERVAL_SEC)
    async def publish_telemetry(self) -> None:
        if not self.redis or not self.bot.is_ready():
            return
        await self.redis.set(TELEMETRY_KEY, json.dumps(self._build_telemetry()), ex=TELEMETRY_TTL_SEC)

    def _build_telemetry(self):
        return {
            "bot_name": str(self.bot.user),
            "bot_id": str(self.bot.user.id) if self.bot.user else None,
            "guild_count": len(self.bot.guilds),
            "user_count": self._total_users(),
            "latency_ms": self._latency_ms(),
            "uptime_sec": self._uptime_sec(),
            "cogs_loaded": self._cog_names(),
            "timestamp": int(time.time()),
        }

    def _total_users(self) -> int:
        return sum(g.member_count or 0 for g in self.bot.guilds)

    def _latency_ms(self) -> float:
        return round(self.bot.latency * 1000, 2)

    def _uptime_sec(self) -> int:
        return int(time.time() - self.started_at)

    def _cog_names(self) -> list[str]:
        return list(self.bot.cogs.keys())

    async def _listen_loop(self) -> None:
        assert self.pubsub is not None
        try:
            async for message in self.pubsub.listen():
                raw_data = self._extract_data(message)
                if raw_data:
                    self._spawn_handler(raw_data)
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("Unexpected error in Redis IPC listener")

    @staticmethod
    def _extract_data(message: dict[str, Any]) -> str | bytes | None:
        if message.get("type") != "message":
            return None
        return message.get("data") or None

    def _spawn_handler(self, raw_data: str | bytes) -> None:
        # Keep a strong reference so the task isn't garbage-collected mid-flight.
        task = asyncio.create_task(self._handle_ipc_request(raw_data))
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)

    async def _handle_ipc_request(self, raw_data: str | bytes) -> None:
        request = IPCRequest.parse(raw_data)
        if request is None:
            return
        reply = await self._execute(request)
        await self._publish_reply(request, reply)

    async def _execute(self, request: IPCRequest):
        t0 = time.perf_counter()
        try:
            handler = self._get_handler(request.op)
            data = await handler(request.payload)
        except Exception as exc:
            log.exception("Error executing IPC op %s", request.op)
            return self._error_reply(request, exc)
        return self._success_reply(request, data, t0)

    @staticmethod
    def _success_reply(request: IPCRequest, data: dict[str, Any], t0: float):
        return {
            "corr_id": request.corr_id,
            "ok": True,
            "op": request.op,
            "rtt_ms": elapsed_ms(t0),
            "data": data,
        }

    @staticmethod
    def _error_reply(request: IPCRequest, exc: Exception):
        return {
            "corr_id": request.corr_id,
            "ok": False,
            "op": request.op,
            "error": str(exc),
        }

    async def _publish_reply(self, request: IPCRequest, reply: dict[str, Any]) -> None:
        await self.redis.publish(request.response_channel, json.dumps(reply))

    @staticmethod
    def _serialize_missing_guild(guild_id: int | str):
        return {"bot_present": False, "guild_id": str(guild_id)}

    def _serialize_guild_summary(self, guild: discord.Guild, member: discord.Member | None):
        return {
            "bot_present": True,
            "name": guild.name,
            "member_count": guild.member_count or len(guild.members),
            "owner_id": str(guild.owner_id),
            "text_channels": len(guild.text_channels),
            "voice_channels": len(guild.voice_channels),
            "roles_count": len(guild.roles),
            "boost_tier": guild.premium_tier,
            "bot_joined_at": self._bot_joined_at(guild),
            "user_top_role": member.top_role.name if member else "Member",
            "active_cogs": self._cog_names(),
        }

    def _serialize_guild_detail(self, guild: discord.Guild):
        return {
            "bot_present": True,
            "guild_id": str(guild.id),
            "name": guild.name,
            "member_count": guild.member_count,
            "channels": self._serialize_channels(guild),
            "cogs": self._cog_names(),
        }

    @staticmethod
    def _serialize_channels(guild: discord.Guild) -> list[dict[str, str]]:
        return [{"id": str(ch.id), "name": ch.name, "type": str(ch.type)} for ch in guild.channels[:MAX_DETAIL_CHANNELS]]

    @staticmethod
    def _bot_joined_at(guild: discord.Guild) -> str | None:
        if guild.me and guild.me.joined_at:
            return guild.me.joined_at.isoformat()
        return None

    def _lookup_member(self, guild: discord.Guild, user_id: int | None) -> discord.Member | None:
        return guild.get_member(user_id) if user_id else None

    def _describe_guild_for_user(self, guild_id: int, user_id: int | None):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return {"bot_present": False}
        return self._serialize_guild_summary(guild, self._lookup_member(guild, user_id))

    @ipc_op("PING")
    async def _op_ping(self, _: Mapping):
        return {
            "pong": True,
            "latency_ms": self._latency_ms(),
            "guild_count": len(self.bot.guilds),
        }

    @ipc_op("GET_MUTUAL_GUILDS")
    async def _op_get_mutual_guilds(self, payload: Mapping[str, Any]):
        user_id = parse_int(payload.get("user_id"))
        guilds: dict[str, Any] = {}

        for raw_id in payload.get("guild_ids", []):
            guild_id = parse_int(raw_id)
            if guild_id is None:
                continue
            guilds[str(raw_id)] = self._describe_guild_for_user(guild_id, user_id)

        return {"guilds": guilds, "bot_total_guilds": len(self.bot.guilds)}

    @ipc_op("GET_GUILD_DETAIL")
    async def _op_get_guild_detail(self, payload: Mapping[str, Any]):
        guild_id = require_int(payload, "guild_id")
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return self._serialize_missing_guild(guild_id)
        return self._serialize_guild_detail(guild)


async def setup(bot: Bot) -> None:
    await bot.add_cog(ParrotRedisIPC(bot))
