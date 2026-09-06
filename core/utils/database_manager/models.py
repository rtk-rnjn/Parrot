from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, TypedDict

from bson import ObjectId


class Rule(TypedDict):
    enabled: bool
    name: str

    trigger: dict
    conditions: list[dict]
    effects: list[dict]


class AutomodConfig(TypedDict):
    word_denylist: list[str]
    word_allowlist: list[str]
    website_denylist: list[str]
    website_allowlist: list[str]
    rules: list[Rule]
    logs: list[str]


class CustomCommand(TypedDict):
    name: str
    response: str
    ignored_roles: list[int]
    ignored_channels: list[int]
    enabled: bool


class Tag(TypedDict):
    name: str
    content: str
    nsfw: bool
    creator_id: int
    created_at: datetime
    aliases: list[str]
    used_count: dict[str, int]


class TagUserUsage(TypedDict):
    user_id: int
    count: int


class TopTagUsage(TypedDict):
    name: str
    count: int


class _TagUserUsageRow(TypedDict):
    _id: str
    count: int


class _TopTagUsageRow(TypedDict):
    _id: str
    count: int


class LevelingConfig(TypedDict):
    enabled: bool
    level_roles: dict[str, int]  # level -> role_id


class GiveawayConfig(TypedDict):
    enabled: bool
    giveaway_channel_id: int | None
    giveaway_role_id: int | None


class Giveaway(TypedDict):
    _id: ObjectId
    guild_id: int
    channel_id: int
    message_id: int
    host_id: int
    prize: str
    winners: int
    ends_at: datetime
    entry_mode: Literal["button", "reaction"]
    entrants: list[int]
    ended: bool
    created_at: datetime


class WelcomeConfig(TypedDict):
    enabled: bool
    on_member_join_message: str | None
    on_member_join_channel_id: int | None
    on_member_leave_message: str | None
    on_member_leave_channel_id: int | None


class StarboardConfig(TypedDict):
    enabled: bool
    channel_id: int
    threshold: int
    emoji: str
    board_messages: dict[str, int]


class GuildConfiguration(TypedDict):
    _id: int
    command_prefix: str
    mute_role_id: int | None
    muted_members: list[int]
    violations: dict[str, dict[str, int]]
    automod: AutomodConfig

    leveling_config: LevelingConfig
    giveaway_config: GiveawayConfig
    welcome_config: WelcomeConfig
    starboard_config: StarboardConfig

    custom_commands: list[CustomCommand]
    tags: list[Tag]

    afk_users: dict[str, str]

    events: dict[str, bool]  # event_name -> enabled

    # Meta
    custom_commands_db: dict[str, str]
    custom_commands_logs: list[str]

    leveling_data: dict[str, int]  # user_id -> xp


class TodoStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TodoItem(TypedDict):
    id: ObjectId
    title: str
    notes: str | None
    due: datetime | None
    status: TodoStatus
    created_at: datetime


class Highlight(TypedDict):
    guild_id: int
    words: list[str]


class UserConfiguration(TypedDict):
    _id: int
    timezone: str
    todo_items: list[TodoItem]
    highlights: list[Highlight]
    highlight_ignored_users: list[int]


# For Internal stats


class Command(TypedDict):
    _id: ObjectId
    qualified_name: str
    invoked_by: int
    invoked_at: datetime

    message_id: int
    channel_id: int
    guild_id: int

    message_content: str


class Stats(TypedDict):
    pass
