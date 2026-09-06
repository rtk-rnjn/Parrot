from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from discord.utils import MISSING
from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration, StarboardConfig

DEFAULT_STARBOARD_EMOJI = "⭐"
DEFAULT_STARBOARD_THRESHOLD = 3


class _GuildStarboardMixin:
    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def _cache_starboard_config(self, *, guild_id: int, config: StarboardConfig) -> None:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG.format(guild_id=guild_id)
        await self.redis_client.hset(
            config_key,
            mapping={
                "enabled": int(config["enabled"]),
                "channel_id": config["channel_id"],
                "threshold": config["threshold"],
                "emoji": config["emoji"],
            },
        )

        messages_key = RedisKeys.GUILD_STARBOARD_BOARD_MESSAGES.format(guild_id=guild_id)
        await self.redis_client.delete(messages_key)
        if config["board_messages"]:
            await self.redis_client.hset(messages_key, mapping={key: str(value) for key, value in config["board_messages"].items()})

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

    async def delete_starboard_config(self, guild_id: int, /) -> bool:
        result = await self.guilds_collection.update_one(
            {"_id": guild_id, "starboard_config": {"$exists": True}},
            {"$unset": {"starboard_config": ""}},
        )
        await self._invalidate_starboard_cache(guild_id)
        return result.modified_count > 0

    async def get_starboard_config(self, guild_id: int, /) -> StarboardConfig | None:
        config_key = RedisKeys.GUILD_STARBOARD_CONFIG.format(guild_id=guild_id)
        cached = await self.redis_client.hgetall(config_key)
        if cached:
            messages_key = RedisKeys.GUILD_STARBOARD_BOARD_MESSAGES.format(guild_id=guild_id)
            messages = await self.redis_client.hgetall(messages_key)
            return self._starboard_config_from_values(
                {self._redis_text(key): self._redis_text(value) for key, value in cached.items()},
                {self._redis_text(key): self._redis_text(value) for key, value in messages.items()},
            )

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "starboard_config": {"$exists": True}},
            {"starboard_config": 1},
        )
        if guild is None:
            return None

        config = self._normalise_starboard_config(guild["starboard_config"])
        await self._cache_starboard_config(guild_id=guild_id, config=config)
        return config

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

    @staticmethod
    def _normalise_starboard_config(config: Mapping[str, Any]) -> StarboardConfig:
        return {
            "enabled": bool(config.get("enabled", True)),
            "channel_id": int(config["channel_id"]),
            "threshold": int(config.get("threshold", DEFAULT_STARBOARD_THRESHOLD)),
            "emoji": str(config.get("emoji", DEFAULT_STARBOARD_EMOJI)),
            "board_messages": {str(key): int(value) for key, value in config.get("board_messages", {}).items()},
        }

    @classmethod
    def _starboard_config_from_values(cls, config: Mapping[str, Any], messages: Mapping[str, Any]) -> StarboardConfig:
        return cls._normalise_starboard_config(
            {
                "enabled": bool(int(config["enabled"])),
                "channel_id": int(config["channel_id"]),
                "threshold": int(config["threshold"]),
                "emoji": config["emoji"],
                "board_messages": messages,
            },
        )

    @staticmethod
    def _redis_text(value: object) -> str:
        return value.decode() if isinstance(value, bytes) else str(value)
