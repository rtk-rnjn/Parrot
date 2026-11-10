from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from bson import ObjectId


class Tag(TypedDict):
    _id: ObjectId
    guild_id: int

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


class TagUserUsageRow(TypedDict):
    _id: str
    count: int


class TopTagUsageRow(TypedDict):
    _id: str
    count: int
