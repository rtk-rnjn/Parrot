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
class IPCTelemetry(TypedDict):
    bot_name: str
    bot_id: str | None
    guild_count: int
    user_count: int
    latency_ms: float
    uptime_sec: int
    cogs_loaded: list[str]
    timestamp: int


@type_check_only
class IPCGuildMissing(TypedDict):
    """Bot is not in the guild.

    `guild_id` is only included by guild-scoped ops, not GET_MUTUAL_GUILDS.
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
class IPCGuildChannel(TypedDict):
    id: str
    name: str
    type: str
    category_id: str | None
    category: str | None
    position: int

    bot_can_send: bool | None


@type_check_only
class IPCGuildChannelsResponse(TypedDict):
    bot_present: Literal[True]
    guild_id: str
    channels: list[IPCGuildChannel]


@type_check_only
class IPCGuildChannelsPayload(TypedDict):
    guild_id: str | int

    types: NotRequired[list[str]]


@type_check_only
class IPCRole(TypedDict):
    id: str
    name: str
    color: int
    position: int
    hoist: bool
    managed: bool
    mentionable: bool
    is_default: bool

    assignable: bool

    permissions: str


@type_check_only
class IPCGuildRolesResponse(TypedDict):
    bot_present: Literal[True]
    guild_id: str
    roles: list[IPCRole]


@type_check_only
class IPCMember(TypedDict):
    id: str
    username: str
    display_name: str
    avatar_url: str
    bot: bool
    is_owner: bool
    top_role: str
    role_ids: list[str]
    joined_at: str | None


@type_check_only
class IPCMemberResponse(TypedDict):
    bot_present: Literal[True]

    member: IPCMember | None


@type_check_only
class IPCMemberSearchResponse(TypedDict):
    bot_present: Literal[True]
    members: list[IPCMember]


@type_check_only
class IPCMemberPayload(TypedDict):
    guild_id: str | int
    user_id: str | int


@type_check_only
class IPCMemberSearchPayload(TypedDict):
    guild_id: str | int
    query: str
    limit: NotRequired[int]


@type_check_only
class IPCPermissionsResponse(TypedDict):
    bot_present: Literal[True]
    is_member: bool
    is_owner: bool
    administrator: bool
    manage_guild: bool

    can_manage: bool
    permissions: str


@type_check_only
class IPCPermissionsPayload(TypedDict):
    guild_id: str | int
    user_id: str | int


@type_check_only
class IPCUserInfo(TypedDict):
    id: str
    username: str
    global_name: str | None
    avatar_url: str
    bot: bool
    created_at: str


@type_check_only
class IPCPrefixCommand(TypedDict):
    name: str
    description: str
    help: str
    signature: str
    aliases: list[str]
    cog: str | None


@type_check_only
class IPCSlashCommand(TypedDict):
    name: str
    description: str
    signature: str
    cog: str | None


@type_check_only
class IPCCommandsResponse(TypedDict):
    prefix: list[IPCPrefixCommand]
    slash: list[IPCSlashCommand]
    default_prefix: str


@type_check_only
class IPCEmbedPayload(TypedDict):
    title: NotRequired[str]
    description: NotRequired[str]
    color: NotRequired[int | str]


@type_check_only
class IPCSendMessagePayload(TypedDict):
    guild_id: str | int
    channel_id: str | int

    user_id: str | int
    content: NotRequired[str]
    embed: NotRequired[IPCEmbedPayload]


@type_check_only
class IPCSendMessageResponse(TypedDict):
    bot_present: Literal[True]
    message_id: str
    channel_id: str
    jump_url: str


@type_check_only
class IPCCogInfo(TypedDict):
    name: str
    description: str
    command_count: int


@type_check_only
class IPCCogsResponse(TypedDict):
    cogs: list[IPCCogInfo]
    extensions: list[str]


@type_check_only
class IPCReloadPayload(TypedDict):
    user_id: str | int
    extension: str


@type_check_only
class IPCReloadResponse(TypedDict):
    extension: str
    reloaded: Literal[True]


@type_check_only
class IPCEvent(TypedDict):
    event: Literal["GUILD_JOIN", "GUILD_REMOVE"]
    timestamp: int
    data: dict[str, str | int | None]
