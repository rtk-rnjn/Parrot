from __future__ import annotations

from typing import TypedDict

USER_ID = int
ROLE_ID = int
GUILD_ID = int


class GuildConfiguration(TypedDict):
    _id: GUILD_ID
    command_prefix: str
    mute_role_id: ROLE_ID | None
    muted_members: list[USER_ID]
    voilations: dict[USER_ID, int]
    automod: dict[str, dict]


class UserConfiguration(TypedDict):
    _id: USER_ID
    timezone: str
