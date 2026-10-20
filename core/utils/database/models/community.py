from __future__ import annotations

from datetime import datetime
from typing import Literal, TypedDict

from bson import ObjectId


class LevelingConfig(TypedDict):
    enabled: bool
    channel_id: int | None
    level_roles: dict[str, int]  # level -> role_id


class GiveawayConfig(TypedDict):
    enabled: bool
    giveaway_channel_id: int | None
    giveaway_role_id: int | None


class GiveawayEntry(TypedDict):
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
    winner_ids: list[int]


class WelcomeConfig(TypedDict):
    enabled: bool
    on_member_join_message: str | None
    on_member_join_channel_id: int | None
    on_member_join_role_id: int | None
    on_member_leave_message: str | None
    on_member_leave_channel_id: int | None


class StarboardConfig(TypedDict):
    enabled: bool
    channel_id: int | None
    threshold: int
    emoji: str
    self_star: bool
    allow_nsfw: bool
    max_age_days: int
    ignored_channels: list[int]
    ignored_roles: list[int]
    ignored_users: list[int]


class StarboardEntry(TypedDict):
    _id: ObjectId
    guild_id: int
    source_message_id: int
    board_message_id: int
    source_channel_id: int
    author_id: int
    is_nsfw: bool
    star_count: int
    created_at: datetime
    users: list[int]


class BirthdayConfig(TypedDict):
    enabled: bool
    channel_id: int | None
