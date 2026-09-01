from __future__ import annotations

from typing import TypedDict


class Rule(TypedDict):
    enabled: bool
    name: str

    trigger: dict
    conditions: list[dict]
    effects: list[dict]


class Automod(TypedDict):
    allow_list: list[str]
    deny_list: list[str]

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


class UserConfiguration(TypedDict):
    _id: int
    timezone: str
