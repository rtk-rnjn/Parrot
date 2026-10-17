from __future__ import annotations

from typing import NotRequired, TypedDict


class CustomCommand(TypedDict):
    name: str
    response: str
    ignored_roles: list[int]
    ignored_channels: list[int]
    enabled: bool
    require_prefix: NotRequired[bool]
