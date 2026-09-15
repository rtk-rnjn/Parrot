from __future__ import annotations

import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from ..mixin import DatabaseMixin
from .afk import _GuildAfkMixin  # noqa
from .automod import _GuildAutomodMixin  # noqa
from .birthday import _GuildBirthdayMixin  # noqa
from .custom_commands import _GuildCustomCommandsMixin  # noqa
from .events import _GuildEventsMixin  # noqa
from .giveaway import _GuildGiveawayMixin  # noqa
from .global_chat import _GuildGlobalChatMixin  # noqa
from .hub import _GuildHubMixin  # noqa
from .leveling import _GuildLevelingMixin  # noqa
from .mute import _GuildMuteRoleMixin  # noqa
from .prefix import _GuildPrefixMixin  # noqa
from .starboard import _GuildStarboardMixin  # noqa
from .tags import _GuildTagsMixin  # noqa
from .telephone import _GuildTelephoneMixin  # noqa
from .violation import _GuildViolationMixin  # noqa
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
    _GuildViolationMixin,
    _GuildTagsMixin,
    _GuildAutomodMixin,
    _GuildAfkMixin,
    _GuildGiveawayMixin,
    _GuildHubMixin,
    _GuildLevelingMixin,
    _GuildWelcomerMixin,
    _GuildStarboardMixin,
    _GuildBirthdayMixin,
    _GuildGlobalChatMixin,
    _GuildTelephoneMixin,
    _GuildEventsMixin,
    DatabaseMixin,
):
    def create_guild_configuration(self, guild_id: int) -> GuildConfiguration:
        return {
            "_id": guild_id,
            "command_prefix": DEFAULT_PREFIX,
            "mute_role_id": None,
            "hub_channel_id": None,
            "hub_channel_owners": {},
            "global_chat_config": {
                "enabled": False,
                "channel_id": None,
                "webhook_uri": None,
            },
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
            "events": {
                "on_member_join": {"enabled": False, "webhook_uri": None},
                "on_member_leave": {"enabled": False, "webhook_uri": None},
                "on_member_ban": {"enabled": False, "webhook_uri": None},
                "on_member_unban": {"enabled": False, "webhook_uri": None},
                "on_message_delete": {"enabled": False, "webhook_uri": None},
                "on_message_edit": {"enabled": False, "webhook_uri": None},
                "on_channel_delete": {"enabled": False, "webhook_uri": None},
                "on_channel_create": {"enabled": False, "webhook_uri": None},
                "on_channel_update": {"enabled": False, "webhook_uri": None},
                "on_thread_create": {"enabled": False, "webhook_uri": None},
                "on_thread_delete": {"enabled": False, "webhook_uri": None},
                "on_thread_update": {"enabled": False, "webhook_uri": None},
                "on_server_update": {"enabled": False, "webhook_uri": None},
                "on_webhook_update": {"enabled": False, "webhook_uri": None},
                "on_role_create": {"enabled": False, "webhook_uri": None},
                "on_role_delete": {"enabled": False, "webhook_uri": None},
                "on_role_update": {"enabled": False, "webhook_uri": None},
                "on_member_join_voice": {"enabled": False, "webhook_uri": None},
                "on_member_leave_voice": {"enabled": False, "webhook_uri": None},
                "on_member_move_voice": {"enabled": False, "webhook_uri": None},
            },
            "leveling_data": {},
            "telephone_config": {
                "enabled": False,
                "channel_id": None,
                "blocked_servers": [],
            },
            "custom_commands_db": {},
            "custom_commands_logs": [],
        }

    def empty_guild_config(self, guild_id: int) -> GuildConfiguration:
        """Compatibility alias for :meth:`create_guild_configuration`."""
        return self.create_guild_configuration(guild_id)
