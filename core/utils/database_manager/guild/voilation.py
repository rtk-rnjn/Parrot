from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration


class _GuildVoilationMixin:
    """Guild command prefix operations."""

    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def increase_voilation(self, *, guild_id: int, voilation_name: str = "default", user_id: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$inc": {f"violations.{voilation_name}.{user_id}": 1}},
            upsert=True,
        )

        key = RedisKeys.GUILD_MEMBER_VOILATION_COUNT.format(guild_id=guild_id, user_id=user_id, voilation_name=voilation_name)
        await self.redis_client.incr(key)

    async def reset_voilation(self, *, guild_id: int, voilation_name: str = "default", user_id: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"violations.{voilation_name}.{user_id}": 0}},
            upsert=True,
        )

        key = RedisKeys.GUILD_MEMBER_VOILATION_COUNT.format(guild_id=guild_id, user_id=user_id, voilation_name=voilation_name)
        await self.redis_client.set(key, 0)

    async def decrease_voilation(self, *, guild_id: int, voilation_name: str = "default", user_id: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$inc": {f"violations.{voilation_name}.{user_id}": -1}},
            upsert=True,
        )

        key = RedisKeys.GUILD_MEMBER_VOILATION_COUNT.format(guild_id=guild_id, user_id=user_id, voilation_name=voilation_name)
        await self.redis_client.decr(key)

    async def set_voilation_count(self, *, guild_id: int, voilation_name: str = "default", user_id: int, count: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"violations.{voilation_name}.{user_id}": count}},
            upsert=True,
        )

        key = RedisKeys.GUILD_MEMBER_VOILATION_COUNT.format(guild_id=guild_id, user_id=user_id, voilation_name=voilation_name)
        await self.redis_client.set(key, count)

    async def get_voilation_count(self, *, guild_id: int, voilation_name: str = "default", user_id: int) -> int:
        key = RedisKeys.GUILD_MEMBER_VOILATION_COUNT.format(guild_id=guild_id, user_id=user_id, voilation_name=voilation_name)
        count = await self.redis_client.get(key)

        if count is not None:
            return int(count)

        guild_config = await self.guilds_collection.find_one({"_id": guild_id, "violations": {"$exists": True}}, {"violations": 1})
        if guild_config is None:
            return 0

        violations = guild_config["violations"]
        count = violations.get(voilation_name, {}).get(str(user_id), 0)

        await self.redis_client.set(key, count)
        return count
