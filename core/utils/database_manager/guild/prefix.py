from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration


class _GuildPrefixMixin:
    """Guild command prefix operations."""

    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def get_command_prefix(self, *, guild_id: int) -> str | None:
        redis_key = RedisKeys.GUILD_COMMAND_PREFIX.format(guild_id=guild_id)

        cached = await self.redis_client.get(redis_key)
        if cached is not None and isinstance(cached, str):
            return cached

        guild_config = await self.guilds_collection.find_one({"_id": guild_id, "command_prefix": {"$exists": True}}, {"command_prefix": 1})
        if guild_config is None:
            return None

        command_prefix = guild_config["command_prefix"]
        _ = await self.redis_client.set(redis_key, command_prefix)
        return command_prefix

    async def set_command_prefix(self, *, guild_id: int, command_prefix: str) -> None:
        redis_key = RedisKeys.GUILD_COMMAND_PREFIX.format(guild_id=guild_id)

        _ = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {"command_prefix": command_prefix}},
            upsert=True,
        )

        _ = await self.redis_client.set(redis_key, command_prefix)
