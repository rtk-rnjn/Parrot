from __future__ import annotations

from typing import NotRequired, TypedDict

from bson import ObjectId


class CustomCommand(TypedDict):
    _id: ObjectId
    guild_id: int
    name: str
    response: str
    ignored_roles: list[int]
    ignored_channels: list[int]
    enabled: bool
    require_prefix: NotRequired[bool]
