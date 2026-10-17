from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, TypedDict

from bson import ObjectId

from ._common import DiscordId


class TodoStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TodoPriority(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TodoItem(TypedDict):
    id: ObjectId
    title: str
    notes: str | None
    due: datetime | None
    status: TodoStatus
    priority: TodoPriority
    created_at: datetime
    completed_at: datetime | None


class Highlight(TypedDict):
    guild_id: int
    words: list[str]


class SupercellAccount(TypedDict):
    tag: str
    verified: bool
    linked_at: datetime


class SupercellGame(TypedDict):
    clash_royale: SupercellAccount | None
    clash_of_clans: SupercellAccount | None


class ChessAccount(TypedDict):
    username: str
    verified: bool
    code: str | None
    linked_at: datetime


class WeatherSettings(TypedDict, total=False):
    location: dict[str, Any]
    units: str
    lang: str


class UserConfiguration(TypedDict):
    _id: DiscordId
    birthday: str
    timezone: str
    todo_items: list[TodoItem]
    highlights: list[Highlight]
    highlight_ignored_users: list[int]
    supercell: SupercellGame
    chess_com: ChessAccount | None
    weather: WeatherSettings
