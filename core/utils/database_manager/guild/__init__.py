from __future__ import annotations

import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from .afk import _GuildAfkMixin  # noqa
from .automod import _GuildAutomodMixin  # noqa
from .birthday import _GuildBirthdayMixin  # noqa
from .custom_commands import _GuildCustomCommandsMixin  # noqa
from .giveaway import _GuildGiveawayMixin  # noqa
from .leveling import _GuildLevelingMixin  # noqa
from .mute import _GuildMuteRoleMixin  # noqa
from .prefix import _GuildPrefixMixin  # noqa
from .starboard import _GuildStarboardMixin  # noqa
from .tags import _GuildTagsMixin  # noqa
from .voilation import _GuildVoilationMixin  # noqa
from .welcomer import _GuildWelcomerMixin  # noqa

if TYPE_CHECKING:
    from ..models import GuildConfiguration

load_dotenv()

DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", "$")

__all__ = ("_GuildMixin",)


class _GuildMixin(
    _GuildPrefixMixin,
    _GuildCustomCommandsMixin,
    _GuildMuteRoleMixin,
    _GuildVoilationMixin,
    _GuildTagsMixin,
    _GuildAutomodMixin,
    _GuildAfkMixin,
    _GuildGiveawayMixin,
    _GuildLevelingMixin,
    _GuildWelcomerMixin,
    _GuildStarboardMixin,
    _GuildBirthdayMixin,
):
    def empty_guild_config(self, guild_id: int) -> GuildConfiguration:
        return {
            "_id": guild_id,
            "command_prefix": DEFAULT_PREFIX,
            "mute_role_id": None,
            "muted_members": [],
            "violations": {},
            "automod": {
                "word_allowlist": [],
                "word_denylist": [],
                "website_allowlist": [],
                "website_denylist": [],
                "rules": [],
                "logs": [],
            },
            "leveling_config": {
                "enabled": False,
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
                "emoji": "",
                "board_messages": {},
            },
            "birthday_config": {
                "enabled": False,
                "channel_id": None,
            },
            "custom_commands": [],
            "tags": [],
            "afk_users": {},
            "events": {},
            "leveling_data": {},
            "custom_commands_db": {},
            "custom_commands_logs": [],
        }

    async def get_guild_config(self, guild_id: int) -> GuildConfiguration | None:
        return await self.guilds_collection.find_one({"_id": guild_id})
