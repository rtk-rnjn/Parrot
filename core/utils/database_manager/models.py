from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TypedDict

from bson import ObjectId


class Rule(TypedDict):
    enabled: bool
    name: str

    trigger: dict
    conditions: list[dict]
    effects: list[dict]


class Automod(TypedDict):
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


class GuildConfiguration(TypedDict):
    _id: int
    command_prefix: str
    mute_role_id: int | None
    muted_members: list[int]
    violations: dict[str, dict[str, int]]
    automod: Automod
    custom_commands: list[CustomCommand]
    custom_commands_db: dict[str, object]
    custom_commands_logs: list[str]


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
    parent_id: ObjectId | None


class UserConfiguration(TypedDict):
    _id: int
    timezone: str
    todo_items: list[TodoItem]
