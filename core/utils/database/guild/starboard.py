from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from bson import ObjectId
from discord.utils import MISSING

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin

if TYPE_CHECKING:
    from ..models import StarboardConfig, StarboardEntry


class _GuildStarboardMixin(DatabaseMixin):
    async def __cache_starboard_config(self, *, guild_id: int, config: StarboardConfig) -> None:
        enabled_key = RedisKeys.GUILD_STARBOARD_CONFIG_ENABLED.format(guild_id=guild_id)
        await self.redis_client.set(enabled_key, int(config["enabled"]))

        channel_key = RedisKeys.GUILD_STARBOARD_CONFIG_CHANNEL_ID.format(guild_id=guild_id)
        if config["channel_id"] is not None:
            await self.redis_client.set(channel_key, config["channel_id"])

        if config["threshold"] is not None:
            threshold_key = RedisKeys.GUILD_STARBOARD_CONFIG_THRESHOLD.format(guild_id=guild_id)
            await self.redis_client.set(threshold_key, config["threshold"])

        if config["emoji"] is not None:
            emoji_key = RedisKeys.GUILD_STARBOARD_CONFIG_EMOJI.format(guild_id=guild_id)
            await self.redis_client.set(emoji_key, config["emoji"])

        self_star_key = RedisKeys.GUILD_STARBOARD_CONFIG_SELF_STAR.format(guild_id=guild_id)
        await self.redis_client.set(self_star_key, int(config["self_star"]))

        allow_nsfw_key = RedisKeys.GUILD_STARBOARD_CONFIG_ALLOW_NSFW.format(guild_id=guild_id)
        await self.redis_client.set(allow_nsfw_key, int(config["allow_nsfw"]))

        max_age_days_key = RedisKeys.GUILD_STARBOARD_CONFIG_MAX_AGE_DAYS.format(guild_id=guild_id)
        if config["max_age_days"] is not None:
            await self.redis_client.set(max_age_days_key, config["max_age_days"])

        if config["ignored_channels"]:
            ignored_channels_key = RedisKeys.GUILD_STARBOARD_CONFIG_IGNORED_CHANNELS.format(guild_id=guild_id)
            await self.redis_client.sadd(ignored_channels_key, *config["ignored_channels"])

        if config["ignored_roles"]:
            ignored_roles_key = RedisKeys.GUILD_STARBOARD_CONFIG_IGNORED_ROLES.format(guild_id=guild_id)
            await self.redis_client.sadd(ignored_roles_key, *config["ignored_roles"])

        if config["ignored_users"]:
            ignored_users_key = RedisKeys.GUILD_STARBOARD_CONFIG_IGNORED_USERS.format(guild_id=guild_id)
            await self.redis_client.sadd(ignored_users_key, *config["ignored_users"])

    async def __invalidate_starboard_cache(self, guild_id: int) -> None:
        keys_to_delete = [
            RedisKeys.GUILD_STARBOARD_CONFIG_ENABLED.format(guild_id=guild_id),
            RedisKeys.GUILD_STARBOARD_CONFIG_CHANNEL_ID.format(guild_id=guild_id),
            RedisKeys.GUILD_STARBOARD_CONFIG_THRESHOLD.format(guild_id=guild_id),
            RedisKeys.GUILD_STARBOARD_CONFIG_EMOJI.format(guild_id=guild_id),
            RedisKeys.GUILD_STARBOARD_CONFIG_SELF_STAR.format(guild_id=guild_id),
            RedisKeys.GUILD_STARBOARD_CONFIG_ALLOW_NSFW.format(guild_id=guild_id),
            RedisKeys.GUILD_STARBOARD_CONFIG_MAX_AGE_DAYS.format(guild_id=guild_id),
            RedisKeys.GUILD_STARBOARD_CONFIG_IGNORED_CHANNELS.format(guild_id=guild_id),
            RedisKeys.GUILD_STARBOARD_CONFIG_IGNORED_ROLES.format(guild_id=guild_id),
            RedisKeys.GUILD_STARBOARD_CONFIG_IGNORED_USERS.format(guild_id=guild_id),
        ]
        await self.redis_client.delete(*keys_to_delete)

    async def edit_starboard_config(
        self,
        *,
        guild_id: int,
        enabled: bool = MISSING,
        channel_id: int | None = MISSING,
        threshold: int | None = MISSING,
        emoji: str | None = MISSING,
        self_star: bool | None = MISSING,
        allow_nsfw: bool | None = MISSING,
        max_age_days: int | None = MISSING,
        ignored_channels: list[int] = MISSING,
        ignored_roles: list[int] = MISSING,
        ignored_users: list[int] = MISSING,
    ) -> bool:
        updates = {}
        for field, value in (
            ("enabled", enabled),
            ("channel_id", channel_id),
            ("threshold", threshold),
            ("emoji", emoji),
            ("self_star", self_star),
            ("allow_nsfw", allow_nsfw),
            ("max_age_days", max_age_days),
            ("ignored_channels", ignored_channels),
            ("ignored_roles", ignored_roles),
            ("ignored_users", ignored_users),
        ):
            if value is not MISSING:
                updates[f"starboard_config.{field}"] = value
        if not updates:
            return False

        result = await self.guilds_collection.update_one({"_id": guild_id}, {"$set": updates}, upsert=True)
        if result.matched_count == 0 and result.upserted_id is None:
            return False

        await self.__invalidate_starboard_cache(guild_id)
        return True

    async def is_starboard_enabled(self, guild_id: int, /) -> bool:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG_ENABLED.format(guild_id=guild_id)
        cached = await self.redis_client.get(config_key)
        if cached is not None:
            return bool(int(cached))

        guild = await self.guilds_collection.find_one({"_id": guild_id}, {"starboard_config.enabled": 1})
        if guild is None:
            return False

        enabled = bool(guild["starboard_config"]["enabled"])
        await self.redis_client.set(config_key, int(enabled))
        return enabled

    async def get_starboard_board_channel_id(self, guild_id: int, /) -> int | None:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG_CHANNEL_ID.format(guild_id=guild_id)
        cached = await self.redis_client.get(config_key)
        if cached is not None:
            return int(cached)

        guild = await self.guilds_collection.find_one({"_id": guild_id}, {"starboard_config.channel_id": 1})
        if guild is None:
            return None

        channel_id = guild["starboard_config"]["channel_id"]
        if channel_id is not None:
            await self.redis_client.set(config_key, channel_id)
        return channel_id

    async def get_starboard_emoji(self, guild_id: int, /) -> str | None:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG_EMOJI.format(guild_id=guild_id)
        cached = await self.redis_client.get(config_key)
        if cached is not None and isinstance(cached, str):
            return cached

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "starboard_config.emoji": {"$exists": True}},
            {"starboard_config.emoji": 1},
        )
        if guild is None:
            return None

        emoji = guild["starboard_config"]["emoji"]
        if emoji is not None:
            await self.redis_client.set(config_key, emoji)
        return emoji

    async def get_starboard_threshold(self, guild_id: int, /) -> int | None:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG_THRESHOLD.format(guild_id=guild_id)
        cached = await self.redis_client.get(config_key)
        if cached is not None:
            return int(cached)

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "starboard_config.threshold": {"$exists": True}},
            {"starboard_config.threshold": 1},
        )
        if guild is None:
            return None

        threshold = guild["starboard_config"]["threshold"]
        await self.redis_client.set(config_key, threshold)
        return threshold

    async def is_starboard_self_star_enabled(self, guild_id: int, /) -> bool:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG_SELF_STAR.format(guild_id=guild_id)
        cached = await self.redis_client.get(config_key)
        if cached is not None:
            return bool(int(cached))

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "starboard_config.self_star": {"$exists": True}},
            {"starboard_config.self_star": 1},
        )
        if guild is None:
            return False

        self_star = bool(guild["starboard_config"]["self_star"])
        await self.redis_client.set(config_key, int(self_star))
        return self_star

    async def is_starboard_nsfw_allowed(self, guild_id: int, /) -> bool:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG_ALLOW_NSFW.format(guild_id=guild_id)
        cached = await self.redis_client.get(config_key)
        if cached is not None:
            return bool(int(cached))

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "starboard_config.allow_nsfw": {"$exists": True}},
            {"starboard_config.allow_nsfw": 1},
        )
        if guild is None:
            return False

        allow_nsfw = bool(guild["starboard_config"]["allow_nsfw"])
        await self.redis_client.set(config_key, int(allow_nsfw))
        return allow_nsfw

    async def get_starboard_max_age_days(self, guild_id: int, /) -> int | None:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG_MAX_AGE_DAYS.format(guild_id=guild_id)
        cached = await self.redis_client.get(config_key)
        if cached is not None:
            return int(cached)

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "starboard_config.max_age_days": {"$exists": True}},
            {"starboard_config.max_age_days": 1},
        )
        if guild is None:
            return None

        max_age_days = guild["starboard_config"]["max_age_days"]
        if max_age_days is not None:
            await self.redis_client.set(config_key, max_age_days)
        return max_age_days

    async def get_starboard_ignored_channels(self, guild_id: int, /) -> list[int]:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG_IGNORED_CHANNELS.format(guild_id=guild_id)
        cached = await self.redis_client.smembers(config_key)
        if cached:
            return [int(channel_id) for channel_id in cached]

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "starboard_config.ignored_channels": {"$exists": True}},
            {"starboard_config.ignored_channels": 1},
        )
        if guild is None:
            return []

        ignored_channels = guild["starboard_config"]["ignored_channels"]
        if ignored_channels:
            await self.redis_client.sadd(config_key, *ignored_channels)
        return ignored_channels

    async def get_starboard_ignored_roles(self, guild_id: int, /) -> list[int]:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG_IGNORED_ROLES.format(guild_id=guild_id)
        cached = await self.redis_client.smembers(config_key)
        if cached:
            return [int(role_id) for role_id in cached]

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "starboard_config.ignored_roles": {"$exists": True}},
            {"starboard_config.ignored_roles": 1},
        )
        if guild is None:
            return []

        ignored_roles = guild["starboard_config"]["ignored_roles"]
        if ignored_roles:
            await self.redis_client.sadd(config_key, *ignored_roles)
        return ignored_roles

    async def get_starboard_ignored_users(self, guild_id: int, /) -> list[int]:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG_IGNORED_USERS.format(guild_id=guild_id)
        cached = await self.redis_client.smembers(config_key)
        if cached:
            return [int(user_id) for user_id in cached]

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "starboard_config.ignored_users": {"$exists": True}},
            {"starboard_config.ignored_users": 1},
        )
        if guild is None:
            return []

        ignored_users = guild["starboard_config"]["ignored_users"]
        if ignored_users:
            await self.redis_client.sadd(config_key, *ignored_users)
        return ignored_users

    # Entries

    def get_current_utc_time(self):
        return discord.utils.utcnow()

    def generate_object_id(self):
        return ObjectId()

    async def add_starboard_entry(
        self,
        *,
        guild_id: int,
        source_message_id: int,
        board_message_id: int,
        source_channel_id: int,
        author_id: int,
        users: list[int] | None = None,
        star_count: int | None = None,
        is_nsfw: bool = False,
    ) -> None:
        users = users or []
        entry: StarboardEntry = {
            "_id": self.generate_object_id(),
            "guild_id": guild_id,
            "source_message_id": source_message_id,
            "source_channel_id": source_channel_id,
            "author_id": author_id,
            "board_message_id": board_message_id,
            "users": users,
            "created_at": self.get_current_utc_time(),
            "is_nsfw": is_nsfw,
            "star_count": len(users) if star_count is None else star_count,
        }
        await self.starboards_collection.insert_one(entry)

    async def get_starboard_entry(self, *, guild_id: int, source_message_id: int) -> StarboardEntry | None:
        return await self.starboards_collection.find_one({"guild_id": guild_id, "source_message_id": source_message_id})

    async def add_user_to_starboard_entry(self, *, guild_id: int, source_message_id: int, user_id: int) -> None:
        await self.starboards_collection.update_one(
            {"guild_id": guild_id, "source_message_id": source_message_id},
            {
                "$addToSet": {"users": user_id},
                "$inc": {"star_count": 1},
            },
        )

    async def remove_user_from_starboard_entry(self, *, guild_id: int, source_message_id: int, user_id: int) -> None:
        await self.starboards_collection.update_one(
            {"guild_id": guild_id, "source_message_id": source_message_id},
            {
                "$pull": {"users": user_id},
                "$inc": {"star_count": -1},
            },
        )

    async def delete_starboard_entry(self, *, guild_id: int, source_message_id: int) -> None:
        await self.starboards_collection.delete_one({"guild_id": guild_id, "source_message_id": source_message_id})

    async def get_starboard_entries_by_guild(self, guild_id: int, /) -> list[StarboardEntry]:
        cursor = self.starboards_collection.find({"guild_id": guild_id})
        return await cursor.to_list(length=None)

    async def get_starboard_entries_by_user(self, guild_id: int, user_id: int, /) -> list[StarboardEntry]:
        cursor = self.starboards_collection.find({"guild_id": guild_id, "author_id": user_id})
        return await cursor.to_list(length=None)

    async def get_starboard_entry_star_count(self, *, guild_id: int, source_message_id: int) -> int:
        entry = await self.starboards_collection.find_one(
            {"guild_id": guild_id, "source_message_id": source_message_id},
            {"star_count": 1},
        )
        if entry is None:
            return 0
        return entry.get("star_count", 0)

    async def is_starboard_entry_nsfw(self, *, guild_id: int, source_message_id: int) -> bool:
        entry = await self.starboards_collection.find_one(
            {"guild_id": guild_id, "source_message_id": source_message_id},
            {"is_nsfw": 1},
        )
        if entry is None:
            return False
        return entry.get("is_nsfw", False)

    async def get_starboard_entry_by_board_message_id(self, *, guild_id: int, board_message_id: int) -> StarboardEntry | None:
        return await self.starboards_collection.find_one({"guild_id": guild_id, "board_message_id": board_message_id})
