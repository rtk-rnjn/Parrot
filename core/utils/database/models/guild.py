from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from bson import ObjectId

from ._common import DiscordId
from .automod import AutomodConfig
from .chat import GlobalChatConfig, TelephoneConfig, TicketConfig
from .commands import CustomCommand
from .community import BirthdayConfig, GiveawayConfig, LevelingConfig, StarboardConfig, WelcomeConfig
from .events import Events
from .tags import Tag


class ModeratorConfig(TypedDict):
    moderator_role_ids: list[int]
    moderator_logs_channel_id: int | None
    mute_role_id: int | None


class UserViolation(TypedDict):
    _id: ObjectId
    violation_name: str  # default name is "default"
    user_id: int
    issued_at: datetime
    issued_by: int | None  # moderator id, None if issued by automod
    expires_at: datetime | None

    metadata: dict[str, str]  # optional metadata for the violation, e.g. rule name, reason, etc.


class GuildConfiguration(TypedDict):
    _id: DiscordId
    command_prefix: str
    hub_channel_id: int | None
    suggestion_channel_id: int | None

    hub_channel_owners: dict[str, int]  # channel_id -> owner_id

    muted_members: list[int]
    user_violations: list[UserViolation]

    moderator_config: ModeratorConfig
    automod: AutomodConfig

    leveling_config: LevelingConfig
    giveaway_config: GiveawayConfig
    welcome_config: WelcomeConfig
    starboard_config: StarboardConfig
    birthday_config: BirthdayConfig
    global_chat_config: GlobalChatConfig
    telephone_config: TelephoneConfig
    ticket_config: TicketConfig

    custom_commands: list[CustomCommand]
    tags: list[Tag]

    afk_users: dict[str, str]

    events: Events
    leveling_data: dict[str, int]  # user_id -> xp

    # Meta
    custom_commands_db: dict[str, str]
    custom_commands_logs: list[str]
    mod_case_counter: int


class ModAction(TypedDict):
    _id: ObjectId
    guild_id: int
    case_id: int
    action: str
    moderator_id: int | None
    target_ids: list[int]
    reason: str | None
    created_at: datetime
    expires_at: datetime | None
    metadata: dict[str, str]
