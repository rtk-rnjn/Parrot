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
from discord import app_commands
from discord.ext import commands, tasks

if TYPE_CHECKING:
    from core import Bot

    from .type import (
        IPCChannel,
        IPCCogsResponse,
        IPCCommandsResponse,
        IPCErrorReply,
        IPCEvent,
        IPCGuildChannel,
        IPCGuildChannelsResponse,
        IPCGuildDetail,
        IPCGuildDetailResponse,
        IPCGuildMissing,
        IPCGuildRolesResponse,
        IPCGuildSummary,
        IPCMember,
        IPCMemberResponse,
        IPCMemberSearchResponse,
        IPCMutualGuildsResponse,
        IPCPermissionsResponse,
        IPCPingResponse,
        IPCPrefixCommand,
        IPCReloadResponse,
        IPCReply,
        IPCRole,
        IPCSendMessageResponse,
        IPCSlashCommand,
        IPCSuccessReply,
        IPCTelemetry,
        IPCUserInfo,
    )


log = logging.getLogger(__name__)

IPC_REQUEST_CHANNEL = "bot:ipc:request"
IPC_EVENTS_CHANNEL = "bot:ipc:events"
IPC_RESPONSE_PREFIX = "bot:ipc:response"
TELEMETRY_KEY = "bot:telemetry:status"
TELEMETRY_INTERVAL_SEC = 15.0
TELEMETRY_TTL_SEC = 60
MAX_DETAIL_CHANNELS = 25
MAX_MESSAGE_LENGTH = 2000
DEFAULT_MEMBER_LIMIT = 10
MAX_MEMBER_LIMIT = 25


class IPCError(ValueError):
    """Expected, user-facing failure (bad payload, missing permission, ...).

    Reported back to the caller as an error reply and logged as a warning
    instead of a full traceback.
    """


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
        raise IPCError(message)
    return value


def elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


class InterProcessIntegration(commands.Cog):
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
        self._listener_task = asyncio.create_task(self._listen_loop())

    def _stop_listener(self) -> None:
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()

    def _cancel_pending(self) -> None:
        for task in self._pending:
            task.cancel()

    def _collect_handlers(self):
        return {
            getattr(method, "__ipc_operation__"): method  # noqa: B009
            for _, method in inspect.getmembers(self, predicate=inspect.iscoroutinefunction)
            if getattr(method, "__ipc_operation__", None) is not None
        }

    def _get_handler(self, op: str):
        handler = self._handlers.get(op)
        if handler is None:
            message = f"Unsupported IPC operation: {op}"
            raise IPCError(message)
        return handler

    @tasks.loop(seconds=TELEMETRY_INTERVAL_SEC)
    async def publish_telemetry(self) -> None:
        if not self.redis or not self.bot.is_ready():
            return
        await self.redis.set(TELEMETRY_KEY, json.dumps(self._build_telemetry()), ex=TELEMETRY_TTL_SEC)

    def _build_telemetry(self) -> IPCTelemetry:
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

    async def _execute(self, request: IPCRequest) -> IPCReply:
        t0 = time.perf_counter()
        try:
            handler = self._get_handler(request.op)
            data = await handler(request.payload)
        except IPCError as exc:
            log.warning("IPC op %s rejected: %s", request.op, exc)
            return self._error_reply(request, exc)
        except Exception as exc:
            log.exception("Error executing IPC op %s", request.op)
            return self._error_reply(request, exc)
        return self._success_reply(request, data, t0)

    @staticmethod
    def _success_reply(request: IPCRequest, data: dict[str, Any], t0: float) -> IPCSuccessReply:
        return {
            "corr_id": request.corr_id,
            "ok": True,
            "op": request.op,
            "rtt_ms": elapsed_ms(t0),
            "data": data,
        }

    @staticmethod
    def _error_reply(request: IPCRequest, exc: Exception) -> IPCErrorReply:
        return {
            "corr_id": request.corr_id,
            "ok": False,
            "op": request.op,
            "error": str(exc),
        }

    async def _publish_reply(self, request: IPCRequest, reply: IPCReply) -> None:
        await self.redis.publish(request.response_channel, json.dumps(reply))

    async def _publish_event(self, event: str, data: dict[str, str | int | None]) -> None:
        payload: IPCEvent = {"event": event, "timestamp": int(time.time()), "data": data}  # type: ignore[typeddict-item]
        try:
            await self.redis.publish(IPC_EVENTS_CHANNEL, json.dumps(payload))
        except Exception:
            log.exception("Failed to publish IPC event %s", event)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self._publish_event(
            "GUILD_JOIN",
            {"guild_id": str(guild.id), "name": guild.name, "member_count": guild.member_count},
        )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        await self._publish_event(
            "GUILD_REMOVE",
            {"guild_id": str(guild.id), "name": guild.name, "member_count": guild.member_count},
        )

    @staticmethod
    def _serialize_missing_guild(guild_id: int | str) -> IPCGuildMissing:
        return {"bot_present": False, "guild_id": str(guild_id)}

    def _serialize_guild_summary(self, guild: discord.Guild, member: discord.Member | None) -> IPCGuildSummary:
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

    def _serialize_guild_detail(self, guild: discord.Guild) -> IPCGuildDetail:
        return {
            "bot_present": True,
            "guild_id": str(guild.id),
            "name": guild.name,
            "member_count": guild.member_count,
            "channels": self._serialize_channels(guild),
            "cogs": self._cog_names(),
        }

    @staticmethod
    def _serialize_channels(guild: discord.Guild) -> list[IPCChannel]:
        return [{"id": str(ch.id), "name": ch.name, "type": str(ch.type)} for ch in guild.channels[:MAX_DETAIL_CHANNELS]]

    @staticmethod
    def _serialize_guild_channel(guild: discord.Guild, channel: discord.abc.GuildChannel) -> IPCGuildChannel:
        bot_can_send: bool | None = None
        if isinstance(channel, discord.TextChannel) and guild.me is not None:
            bot_can_send = channel.permissions_for(guild.me).send_messages

        category = channel.category
        return {
            "id": str(channel.id),
            "name": channel.name,
            "type": str(channel.type),
            "category_id": str(category.id) if category else None,
            "category": category.name if category else None,
            "position": channel.position,
            "bot_can_send": bot_can_send,
        }

    @staticmethod
    def _serialize_role(guild: discord.Guild, role: discord.Role) -> IPCRole:
        bot_top = guild.me.top_role if guild.me else None
        assignable = bool(bot_top and not role.is_default() and not role.managed and role < bot_top)
        return {
            "id": str(role.id),
            "name": role.name,
            "color": role.colour.value,
            "position": role.position,
            "hoist": role.hoist,
            "managed": role.managed,
            "mentionable": role.mentionable,
            "is_default": role.is_default(),
            "assignable": assignable,
            # String: 64-bit bitfields lose precision as JS numbers.
            "permissions": str(role.permissions.value),
        }

    @staticmethod
    def _serialize_member(guild: discord.Guild, member: discord.Member) -> IPCMember:
        return {
            "id": str(member.id),
            "username": member.name,
            "display_name": member.display_name,
            "avatar_url": member.display_avatar.url,
            "bot": member.bot,
            "is_owner": member.id == guild.owner_id,
            "top_role": member.top_role.name,
            "role_ids": [str(r.id) for r in member.roles if not r.is_default()],
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
        }

    @staticmethod
    def _bot_joined_at(guild: discord.Guild) -> str | None:
        if guild.me and guild.me.joined_at:
            return guild.me.joined_at.isoformat()
        return None

    def _lookup_member(self, guild: discord.Guild, user_id: int | None) -> discord.Member | None:
        return guild.get_member(user_id) if user_id else None

    async def _resolve_member(self, guild: discord.Guild, user_id: int) -> discord.Member | None:
        """Cache first, then fall back to an API fetch. None if not in the guild."""
        member = guild.get_member(user_id)
        if member is not None:
            return member
        try:
            return await guild.fetch_member(user_id)
        except discord.NotFound:
            return None

    @staticmethod
    def _can_manage(member: discord.Member) -> bool:
        perms = member.guild_permissions
        return perms.administrator or perms.manage_guild

    async def _require_manager(self, guild: discord.Guild, user_id: int) -> discord.Member:
        """Bot-side authorization for mutating ops. Raises IPCError if not allowed."""
        member = await self._resolve_member(guild, user_id)
        if member is None or not self._can_manage(member):
            message = "User needs the Manage Server permission in this guild"
            raise IPCError(message)
        return member

    @staticmethod
    def _build_embed(raw: Any) -> discord.Embed | None:
        if not raw:
            return None
        if not isinstance(raw, Mapping):
            message = "'embed' must be an object"
            raise IPCError(message)

        title, description = raw.get("title"), raw.get("description")
        if not (title or description):
            message = "Embed needs a title or description"
            raise IPCError(message)

        embed = discord.Embed(title=title, description=description)
        color = parse_int(raw.get("color"))
        if color is not None:
            embed.colour = discord.Colour(color)
        return embed

    def _describe_guild_for_user(self, guild_id: int, user_id: int | None) -> IPCGuildSummary | IPCGuildMissing:
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return {"bot_present": False}
        return self._serialize_guild_summary(guild, self._lookup_member(guild, user_id))

    @ipc_op("PING")
    async def _op_ping(self, _: Mapping) -> IPCPingResponse:
        return {
            "pong": True,
            "latency_ms": self._latency_ms(),
            "guild_count": len(self.bot.guilds),
        }

    @ipc_op("GET_TELEMETRY")
    async def _op_get_telemetry(self, _: Mapping) -> IPCTelemetry:
        return self._build_telemetry()

    @ipc_op("GET_COMMANDS")
    async def _op_get_commands(self, _: Mapping) -> IPCCommandsResponse:
        prefix: list[IPCPrefixCommand] = [
            {
                "name": cmd.qualified_name,
                "description": cmd.short_doc or "",
                "help": (cmd.help or cmd.short_doc or "").strip(),
                "signature": cmd.signature,
                "aliases": list(cmd.aliases),
                "cog": cmd.cog_name,
            }
            for cmd in self.bot.walk_commands()
            if not cmd.hidden
        ]
        slash: list[IPCSlashCommand] = [
            {
                "name": cmd.qualified_name,
                "description": cmd.description,
                "signature": " ".join(f"<{parameter.name}>" if parameter.required else f"[{parameter.name}]" for parameter in cmd.parameters),
                "cog": getattr(cmd.binding, "qualified_name", None),
            }
            for cmd in self.bot.tree.walk_commands()
            if isinstance(cmd, app_commands.Command)
        ]
        return {"prefix": prefix, "slash": slash, "default_prefix": self.bot.DEFAULT_PREFIX}

    @ipc_op("GET_USER_INFO")
    async def _op_get_user_info(self, payload: Mapping[str, Any]) -> IPCUserInfo:
        user_id = require_int(payload, "user_id")
        user = self.bot.get_user(user_id)
        if user is None:
            try:
                user = await self.bot.fetch_user(user_id)
            except discord.NotFound as exc:
                message = "User not found"
                raise IPCError(message) from exc

        return {
            "id": str(user.id),
            "username": user.name,
            "global_name": user.global_name,
            "avatar_url": user.display_avatar.url,
            "bot": user.bot,
            "created_at": user.created_at.isoformat(),
        }

    @ipc_op("GET_MUTUAL_GUILDS")
    async def _op_get_mutual_guilds(self, payload: Mapping[str, Any]) -> IPCMutualGuildsResponse:
        user_id = parse_int(payload.get("user_id"))
        guilds: dict[str, Any] = {}

        for raw_id in payload.get("guild_ids", []):
            guild_id = parse_int(raw_id)
            if guild_id is None:
                continue
            guilds[str(raw_id)] = self._describe_guild_for_user(guild_id, user_id)

        return {"guilds": guilds, "bot_total_guilds": len(self.bot.guilds)}

    @ipc_op("GET_GUILD_DETAIL")
    async def _op_get_guild_detail(self, payload: Mapping[str, Any]) -> IPCGuildDetailResponse | IPCGuildMissing:
        guild_id = require_int(payload, "guild_id")
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return self._serialize_missing_guild(guild_id)
        return self._serialize_guild_detail(guild)

    @ipc_op("GET_GUILD_CHANNELS")
    async def _op_get_guild_channels(self, payload: Mapping[str, Any]) -> IPCGuildChannelsResponse | IPCGuildMissing:
        guild_id = require_int(payload, "guild_id")
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return self._serialize_missing_guild(guild_id)

        types = payload.get("types")
        if types is not None and not isinstance(types, list):
            message = "'types' must be a list of channel type names"
            raise IPCError(message)

        channels = [ch for ch in guild.channels if types is None or str(ch.type) in types]
        channels.sort(key=lambda ch: ch.position)

        return {
            "bot_present": True,
            "guild_id": str(guild.id),
            "channels": [self._serialize_guild_channel(guild, ch) for ch in channels],
        }

    @ipc_op("GET_GUILD_ROLES")
    async def _op_get_guild_roles(self, payload: Mapping[str, Any]) -> IPCGuildRolesResponse | IPCGuildMissing:
        guild_id = require_int(payload, "guild_id")
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return self._serialize_missing_guild(guild_id)

        # Highest role first, like the Discord UI.
        roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)
        return {
            "bot_present": True,
            "guild_id": str(guild.id),
            "roles": [self._serialize_role(guild, role) for role in roles],
        }

    @ipc_op("GET_GUILD_MEMBER")
    async def _op_get_guild_member(self, payload: Mapping[str, Any]) -> IPCMemberResponse | IPCGuildMissing:
        guild_id = require_int(payload, "guild_id")
        user_id = require_int(payload, "user_id")
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return self._serialize_missing_guild(guild_id)

        member = await self._resolve_member(guild, user_id)
        return {
            "bot_present": True,
            "member": self._serialize_member(guild, member) if member else None,
        }

    @ipc_op("SEARCH_GUILD_MEMBERS")
    async def _op_search_guild_members(self, payload: Mapping[str, Any]) -> IPCMemberSearchResponse | IPCGuildMissing:
        guild_id = require_int(payload, "guild_id")
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return self._serialize_missing_guild(guild_id)

        query = str(payload.get("query") or "").strip()
        if not query:
            message = "'query' is required"
            raise IPCError(message)

        limit = parse_int(payload.get("limit")) or DEFAULT_MEMBER_LIMIT
        limit = max(1, min(limit, MAX_MEMBER_LIMIT))

        # Matches usernames/nicknames that START with the query. Needs the members intent.
        members = await guild.query_members(query=query, limit=limit)
        return {
            "bot_present": True,
            "members": [self._serialize_member(guild, m) for m in members],
        }

    @ipc_op("CHECK_PERMISSIONS")
    async def _op_check_permissions(self, payload: Mapping[str, Any]) -> IPCPermissionsResponse | IPCGuildMissing:
        guild_id = require_int(payload, "guild_id")
        user_id = require_int(payload, "user_id")
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return self._serialize_missing_guild(guild_id)

        member = await self._resolve_member(guild, user_id)
        if member is None:
            return {
                "bot_present": True,
                "is_member": False,
                "is_owner": False,
                "administrator": False,
                "manage_guild": False,
                "can_manage": False,
                "permissions": "0",
            }

        perms = member.guild_permissions
        return {
            "bot_present": True,
            "is_member": True,
            "is_owner": member.id == guild.owner_id,
            "administrator": perms.administrator,
            "manage_guild": perms.manage_guild,
            "can_manage": self._can_manage(member),
            "permissions": str(perms.value),
        }

    @ipc_op("SEND_MESSAGE")
    async def _op_send_message(self, payload: Mapping[str, Any]) -> IPCSendMessageResponse | IPCGuildMissing:
        guild_id = require_int(payload, "guild_id")
        channel_id = require_int(payload, "channel_id")
        user_id = require_int(payload, "user_id")

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return self._serialize_missing_guild(guild_id)

        member = await self._require_manager(guild, user_id)

        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            message = "Channel not found in this guild or is not a text channel"
            raise IPCError(message)

        if not channel.permissions_for(member).send_messages:
            message = "User cannot send messages in that channel"
            raise IPCError(message)
        if guild.me is None or not channel.permissions_for(guild.me).send_messages:
            message = "Bot cannot send messages in that channel"
            raise IPCError(message)

        content = payload.get("content") or discord.utils.MISSING
        embed = self._build_embed(payload.get("embed")) or discord.utils.MISSING
        if content is None and embed is None:
            message = "Message needs 'content' or an 'embed'"
            raise IPCError(message)
        if content is not None and len(content) > MAX_MESSAGE_LENGTH:
            message = f"'content' exceeds {MAX_MESSAGE_LENGTH} characters"
            raise IPCError(message)

        sent = await channel.send(
            content=content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        log.info("IPC SEND_MESSAGE by user %s in guild %s channel %s", user_id, guild_id, channel_id)

        return {
            "bot_present": True,
            "message_id": str(sent.id),
            "channel_id": str(channel.id),
            "jump_url": sent.jump_url,
        }

    async def _require_owner(self, user_id: int) -> None:
        # Bot.is_owner only reads `.id`, so a bare Object is enough.
        if not await self.bot.is_owner(discord.Object(id=user_id)):  # type: ignore[arg-type]
            message = "Bot owner only"
            raise IPCError(message)

    @ipc_op("GET_COGS")
    async def _op_get_cogs(self, _: Mapping) -> IPCCogsResponse:
        return {
            "cogs": [
                {
                    "name": name,
                    "description": cog.description or "",
                    "command_count": len(cog.get_commands()),
                }
                for name, cog in self.bot.cogs.items()
            ],
            "extensions": sorted(self.bot.extensions),
        }

    @ipc_op("RELOAD_EXTENSION")
    async def _op_reload_extension(self, payload: Mapping[str, Any]) -> IPCReloadResponse:
        user_id = require_int(payload, "user_id")
        await self._require_owner(user_id)

        extension = str(payload.get("extension") or "")
        if extension not in self.bot.extensions:
            message = f"Extension not loaded: {extension!r}"
            raise IPCError(message)

        # Reloading this cog cancels the very task that is handling this request,
        # so the reply would never be sent.
        if extension == self.__module__:
            message = "The IPC extension can't reload itself over IPC"
            raise IPCError(message)

        await self.bot.reload_extension(extension)
        log.warning("IPC RELOAD_EXTENSION %s by owner %s", extension, user_id)
        return {"extension": extension, "reloaded": True}


async def setup(bot: Bot) -> None:
    await bot.add_cog(InterProcessIntegration(bot))
