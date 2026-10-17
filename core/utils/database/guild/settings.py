from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

from pymongo.errors import DuplicateKeyError

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin
from .defaults import EVENT_NAMES, default_guild_configuration

if TYPE_CHECKING:
    from ..models import GuildConfiguration

__all__ = ("SETTING_SECTIONS", "GuildSettingSection", "_GuildSettingsMixin")

type GuildSettingSection = Literal[
    "command_prefix",
    "hub_channel_id",
    "suggestion_channel_id",
    "moderator_config",
    "leveling_config",
    "giveaway_config",
    "welcome_config",
    "starboard_config",
    "birthday_config",
    "global_chat_config",
    "telephone_config",
    "ticket_config",
    "events",
]

# Only settings caches; keys holding state (board messages, muted members, pending XP) are left alone.
_SECTION_CACHE_KEYS: dict[str, tuple[RedisKeys, ...]] = {
    "command_prefix": (RedisKeys.GUILD_COMMAND_PREFIX,),
    "hub_channel_id": (RedisKeys.GUILD_HUB_CHANNEL_ID,),
    "suggestion_channel_id": (RedisKeys.GUILD_SUGGESTION_CHANNEL_ID,),
    "moderator_config": (
        RedisKeys.GUILD_MODERATOR_CONFIG_MODERATOR_ROLE_IDS,
        RedisKeys.GUILD_MODERATOR_CONFIG_MODERATOR_LOGS_CHANNEL_ID,
        RedisKeys.GUILD_MODERATOR_CONFIG_MUTE_ROLE_ID,
    ),
    "leveling_config": (
        RedisKeys.GUILD_LEVELING_CONFIG_ENABLED,
        RedisKeys.GUILD_LEVELING_CONFIG_CHANNEL_ID,
        RedisKeys.GUILD_LEVELING_CONFIG_LEVEL_ROLES,
    ),
    "giveaway_config": (
        RedisKeys.GUILD_GIVEAWAY_CONFIG_ENABLED,
        RedisKeys.GUILD_GIVEAWAY_CONFIG_CHANNEL_ID,
        RedisKeys.GUILD_GIVEAWAY_CONFIG_ROLE_ID,
    ),
    "welcome_config": (
        RedisKeys.GUILD_WELCOME_CONFIG_ENABLED,
        RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_MESSAGE,
        RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_CHANNEL_ID,
        RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_ROLE_ID,
        RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_MESSAGE,
        RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_CHANNEL_ID,
    ),
    "starboard_config": (RedisKeys.GUILD_STARBOARD_CONFIG,),
    "birthday_config": (
        RedisKeys.GUILD_BIRTHDAY_CONFIG_ENABLED,
        RedisKeys.GUILD_BIRTHDAY_CONFIG_CHANNEL_ID,
    ),
    "global_chat_config": (
        RedisKeys.GUILD_GLOBAL_CHAT_CONFIG_ENABLED,
        RedisKeys.GUILD_GLOBAL_CHAT_CONFIG_CHANNEL_ID,
        RedisKeys.GUILD_GLOBAL_CHAT_CONFIG_WEBHOOK_URI,
    ),
    "telephone_config": (
        RedisKeys.GUILD_TELEPHONE_CONFIG_ENABLED,
        RedisKeys.GUILD_TELEPHONE_CONFIG_CHANNEL_ID,
        RedisKeys.GUILD_TELEPHONE_CONFIG_BLOCKED_SERVERS,
    ),
    "ticket_config": (
        RedisKeys.GUILD_TICKET_CONFIG_ENABLED,
        RedisKeys.GUILD_TICKET_CONFIG_CHANNEL_ID,
        RedisKeys.GUILD_TICKET_CONFIG_BOT_MESSAGE_ID,
        RedisKeys.GUILD_TICKET_CONFIG_BOT_CHANNEL_ID,
    ),
    "events": (RedisKeys.GUILD_EVENT_ENABLED, RedisKeys.GUILD_EVENT_WEBHOOK_URI),
}

SETTING_SECTIONS: tuple[GuildSettingSection, ...] = cast(tuple[GuildSettingSection, ...], tuple(_SECTION_CACHE_KEYS))

_PRESERVED_FIELDS: dict[str, tuple[str, ...]] = {
    "starboard_config": ("board_messages",),
}


class _GuildSettingsMixin(DatabaseMixin):
    """Whole-document reads and section resets used by the configuration dashboard."""

    async def get_guild_settings(self, guild_id: int, /) -> GuildConfiguration:
        """Return the guild document with every section present.

        Missing or ``None`` sections (older documents, or sections wiped by a delete)
        are filled from the defaults so callers can index them safely. The guild is
        registered if it does not exist yet.
        """
        defaults = default_guild_configuration(guild_id)
        document = await self.guilds_collection.find_one({"_id": guild_id})

        if document is None:
            try:
                await self.guilds_collection.insert_one(defaults)
            except DuplicateKeyError:
                document = await self.guilds_collection.find_one({"_id": guild_id})
            else:
                await self.redis_client.sadd(RedisKeys.REGISTERED_GUILDS, str(guild_id))
                return defaults

        merged = dict(defaults)
        for key, value in (document or {}).items():
            default = defaults.get(key)
            if isinstance(default, dict) and isinstance(value, dict):
                merged[key] = {**default, **value}
            elif value is not None:
                merged[key] = value

        return cast("GuildConfiguration", merged)

    async def reset_guild_setting(self, *, guild_id: int, section: GuildSettingSection) -> None:
        """Restore one settings section to its defaults and drop its cache entries."""
        defaults = default_guild_configuration(guild_id)
        value = defaults[section]

        preserved = _PRESERVED_FIELDS.get(section, ())
        if preserved and isinstance(value, dict):
            document = await self.guilds_collection.find_one({"_id": guild_id}, {section: 1})
            current = (document or {}).get(section) or {}
            value = {**value, **{field: current[field] for field in preserved if field in current}}

        await self.guilds_collection.update_one({"_id": guild_id}, {"$set": {section: value}}, upsert=True)
        await self.__invalidate_section_cache(guild_id=guild_id, section=section)

    async def __invalidate_section_cache(self, *, guild_id: int, section: GuildSettingSection) -> None:
        templates = _SECTION_CACHE_KEYS[section]
        if section == "events":
            keys = [template.format(guild_id=guild_id, event_name=name) for template in templates for name in EVENT_NAMES]
        else:
            keys = [template.format(guild_id=guild_id) for template in templates]

        if keys:
            await self.redis_client.delete(*keys)
