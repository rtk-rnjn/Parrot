from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin
from ..models import GuildConfiguration


class _GuildPrefixMixin(DatabaseMixin):
    """Guild command-prefix operations."""

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
        await self.redis_client.set(redis_key, command_prefix)
        return command_prefix

    async def edit_prefix_config(self, *, guild_id: int, command_prefix: str) -> None:
        redis_key = RedisKeys.GUILD_COMMAND_PREFIX.format(guild_id=guild_id)

        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {"command_prefix": command_prefix}},
            upsert=True,
        )

        await self.redis_client.set(redis_key, command_prefix)
