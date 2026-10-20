from __future__ import annotations

import os
from typing import TYPE_CHECKING, get_args

from dotenv import load_dotenv

from ..models import EventsConfig

if TYPE_CHECKING:
    from ..models import GuildConfiguration

from .events import EVENT_NAME

load_dotenv()

DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", "$")

EVENT_NAMES = get_args(EVENT_NAME)

__all__ = ("DEFAULT_PREFIX", "EVENT_NAMES", "default_guild_configuration")


def _default_event() -> EventsConfig:
    return {"enabled": False, "webhook_uri": None}


def default_guild_configuration(guild_id: int, /) -> GuildConfiguration:
    """Return a fresh guild document with every setting at its default value."""
    return {
        "_id": guild_id,
        "command_prefix": DEFAULT_PREFIX,
        "hub_channel_id": None,
        "suggestion_channel_id": None,
        "hub_channel_owners": {},
        "muted_members": [],
        "user_violations": [],
        "global_chat_config": {
            "enabled": False,
            "channel_id": None,
            "webhook_uri": None,
        },
        "automod": {
            "word_allowlist": [],
            "word_denylist": [],
            "website_allowlist": [],
            "website_denylist": [],
            "custom_lists": {},
            "rules": [],
            "logs": [],
        },
        "mod_case_counter": 0,
        "moderator_config": {
            "moderator_role_ids": [],
            "moderator_logs_channel_id": None,
            "mute_role_id": None,
        },
        "leveling_config": {
            "enabled": False,
            "channel_id": None,
            "level_roles": {},
        },
        "giveaway_config": {
            "enabled": False,
            "giveaway_channel_id": None,
            "giveaway_role_id": None,
        },
        "welcome_config": {
            "enabled": False,
            "on_member_join_message": None,
            "on_member_join_channel_id": None,
            "on_member_join_role_id": None,
            "on_member_leave_message": None,
            "on_member_leave_channel_id": None,
        },
        "starboard_config": {
            "enabled": False,
            "channel_id": None,
            "threshold": 3,
            "emoji": "\N{WHITE MEDIUM STAR}",
            "allow_nsfw": False,
            "self_star": False,
            "max_age_days": 30,
            "ignored_channels": [],
            "ignored_roles": [],
            "ignored_users": [],
        },
        "birthday_config": {"enabled": False, "channel_id": None},
        "ticket_config": {
            "enabled": False,
            "channel_id": None,
            "bot_message_id": None,
            "bot_channel_channel_id": None,
        },
        "custom_commands": [],
        "tags": [],
        "afk_users": {},
        "events": {name: _default_event() for name in EVENT_NAMES},  # pyright: ignore[reportReturnType]
        "leveling_data": {},
        "telephone_config": {
            "enabled": False,
            "channel_id": None,
            "blocked_servers": [],
        },
        "custom_commands_db": {},
        "custom_commands_logs": [],
    }
