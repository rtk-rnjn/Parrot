from __future__ import annotations

from typing import Literal, NotRequired, TypedDict, type_check_only


@type_check_only
class IPCSuccessReply[T](TypedDict):
    corr_id: str
    ok: Literal[True]
    op: str
    rtt_ms: float
    data: T


@type_check_only
class IPCErrorReply(TypedDict):
    corr_id: str
    ok: Literal[False]
    op: str
    error: str


type IPCReply[T] = IPCSuccessReply[T] | IPCErrorReply


@type_check_only
class IPCPingResponse(TypedDict):
    pong: Literal[True]
    latency_ms: float
    guild_count: int


@type_check_only
class IPCGuildMissing(TypedDict):
    """Bot is not in the guild.

    `guild_id` is only included by GET_GUILD_DETAIL, not GET_MUTUAL_GUILDS.
    """

    bot_present: Literal[False]
    guild_id: NotRequired[str]


@type_check_only
class IPCGuildSummary(TypedDict):
    bot_present: Literal[True]
    name: str
    member_count: int
    owner_id: str
    text_channels: int
    voice_channels: int
    roles_count: int
    boost_tier: int
    bot_joined_at: str | None
    user_top_role: str
    active_cogs: list[str]


@type_check_only
class IPCChannel(TypedDict):
    id: str
    name: str
    type: str


@type_check_only
class IPCGuildDetail(TypedDict):
    bot_present: Literal[True]
    guild_id: str
    name: str
    member_count: int | None
    channels: list[IPCChannel]
    cogs: list[str]


@type_check_only
class IPCMutualGuildsResponse(TypedDict):
    guilds: dict[str, IPCGuildSummary | IPCGuildMissing]
    bot_total_guilds: int


type IPCGuildDetailResponse = IPCGuildDetail | IPCGuildMissing


@type_check_only
class IPCMutualGuildsPayload(TypedDict):
    user_id: NotRequired[str | int | None]
    guild_ids: NotRequired[list[str | int]]


@type_check_only
class IPCGuildDetailPayload(TypedDict):
    guild_id: str | int


@type_check_only
class IPCTelemetry(TypedDict):
    bot_name: str
    bot_id: str | None
    guild_count: int
    user_count: int
    latency_ms: float
    uptime_sec: int
    cogs_loaded: list[str]
    timestamp: int
