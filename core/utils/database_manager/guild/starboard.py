from __future__ import annotations

from discord.utils import MISSING
from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration

DEFAULT_STARBOARD_EMOJI = "\N{WHITE MEDIUM STAR}"
DEFAULT_STARBOARD_THRESHOLD = 3


class _GuildStarboardMixin:
    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def _invalidate_starboard_cache(self, guild_id: int, /) -> None:
        await self.redis_client.delete(
            RedisKeys.GUILD_STARBOARD_CONFIG.format(guild_id=guild_id),
            RedisKeys.GUILD_STARBOARD_BOARD_MESSAGES.format(guild_id=guild_id),
        )

    async def edit_starboard_config(
        self,
        *,
        guild_id: int,
        enabled: bool = MISSING,
        channel_id: int = MISSING,
        threshold: int = MISSING,
        emoji: str = MISSING,
    ) -> bool:
        updates = {}
        for field, value in (
            ("enabled", enabled),
            ("channel_id", channel_id),
            ("threshold", threshold),
            ("emoji", emoji),
        ):
            if value is not MISSING:
                updates[f"starboard_config.{field}"] = value
        if not updates:
            return False

        result = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": updates},
            upsert=True,
        )
        if result.matched_count == 0 and result.upserted_id is None:
            return False

        await self._invalidate_starboard_cache(guild_id)
        return True

    async def is_starboard_enabled(self, guild_id: int, /) -> bool:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG.format(guild_id=guild_id)
        cached = await self.redis_client.hget(config_key, "enabled")
        if cached is not None:
            return bool(int(cached))

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id},
            {"starboard_config.enabled": 1},
        )
        if guild is None:
            return False

        enabled = bool(guild.get("starboard_config", {}).get("enabled", True))
        await self.redis_client.hset(config_key, "enabled", int(enabled))
        return enabled

    async def enable_starboard(self, guild_id: int, /) -> None:
        await self.edit_starboard_config(guild_id=guild_id, enabled=True)

    async def disable_starboard(self, guild_id: int, /) -> None:
        await self.edit_starboard_config(guild_id=guild_id, enabled=False)

    async def get_starboard_board_channel_id(self, guild_id: int, /) -> int | None:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG.format(guild_id=guild_id)
        cached = await self.redis_client.hget(config_key, "channel_id")
        if cached is not None:
            return int(cached)

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id},
            {"starboard_config.channel_id": 1},
        )
        if guild is None:
            return None

        channel_id = guild.get("starboard_config", {}).get("channel_id")
        if channel_id is not None:
            await self.redis_client.hset(config_key, "channel_id", channel_id)
        return channel_id

    async def get_starboard_emoji(self, guild_id: int, /) -> str:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG.format(guild_id=guild_id)
        cached = await self.redis_client.hget(config_key, "emoji")
        if cached is not None and isinstance(cached, str):
            return cached

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id},
            {"starboard_config.emoji": 1},
        )
        if guild is None:
            return DEFAULT_STARBOARD_EMOJI

        emoji = guild.get("starboard_config", {}).get("emoji", DEFAULT_STARBOARD_EMOJI)
        await self.redis_client.hset(config_key, "emoji", emoji)
        return emoji

    async def set_starboard_board_channel(self, guild_id: int, channel_id: int, /) -> None:
        await self.edit_starboard_config(guild_id=guild_id, channel_id=channel_id)

    async def get_starboard_threshold(self, guild_id: int, /) -> int:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG.format(guild_id=guild_id)
        cached = await self.redis_client.hget(config_key, "threshold")
        if cached is not None:
            return int(cached)

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id},
            {"starboard_config.threshold": 1},
        )
        if guild is None:
            return DEFAULT_STARBOARD_THRESHOLD

        threshold = guild.get("starboard_config", {}).get("threshold", DEFAULT_STARBOARD_THRESHOLD)
        await self.redis_client.hset(config_key, "threshold", threshold)
        return threshold

    async def set_starboard_emoji(self, *, guild_id: int, emoji: str) -> None:
        await self.edit_starboard_config(guild_id=guild_id, emoji=emoji)

    async def set_starboard_threshold(self, *, guild_id: int, threshold: int) -> None:
        await self.edit_starboard_config(guild_id=guild_id, threshold=threshold)

    async def get_starboard_board_message(self, guild_id: int, source_message_id: int, /) -> int | None:
        messages_key = RedisKeys.GUILD_STARBOARD_BOARD_MESSAGES.format(guild_id=guild_id)
        cached = await self.redis_client.hget(messages_key, str(source_message_id))
        if cached is not None:
            return int(cached)

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, f"starboard_config.board_messages.{source_message_id}": {"$exists": True}},
            {f"starboard_config.board_messages.{source_message_id}": 1},
        )
        if guild is None:
            return None

        board_message_id = guild["starboard_config"]["board_messages"][str(source_message_id)]
        await self.redis_client.hset(messages_key, str(source_message_id), board_message_id)
        return board_message_id

    async def set_starboard_board_message(self, *, guild_id: int, source_message_id: int, board_message_id: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"starboard_config.board_messages.{source_message_id}": board_message_id}},
            upsert=True,
        )
        messages_key = RedisKeys.GUILD_STARBOARD_BOARD_MESSAGES.format(guild_id=guild_id)
        await self.redis_client.hset(messages_key, str(source_message_id), board_message_id)

    async def delete_starboard_board_message(self, *, guild_id: int, source_message_id: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$unset": {f"starboard_config.board_messages.{source_message_id}": ""}},
        )
        messages_key = RedisKeys.GUILD_STARBOARD_BOARD_MESSAGES.format(guild_id=guild_id)
        await self.redis_client.hdel(messages_key, str(source_message_id))
