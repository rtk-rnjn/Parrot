from __future__ import annotations

from ..mixin import DatabaseMixin

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration


class _GuildViolationMixin(DatabaseMixin):
    """Guild violation counters, backed by MongoDB and Redis."""

    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def increase_violation(self, *, guild_id: int, violation_name: str = "default", user_id: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$inc": {f"violations.{violation_name}.{user_id}": 1}},
            upsert=True,
        )

        key = RedisKeys.GUILD_MEMBER_VIOLATION_COUNT.format(guild_id=guild_id, user_id=user_id, violation_name=violation_name)
        await self.redis_client.incr(key)

    async def reset_violation(self, *, guild_id: int, violation_name: str = "default", user_id: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"violations.{violation_name}.{user_id}": 0}},
            upsert=True,
        )

        key = RedisKeys.GUILD_MEMBER_VIOLATION_COUNT.format(guild_id=guild_id, user_id=user_id, violation_name=violation_name)
        await self.redis_client.set(key, 0)

    async def decrease_violation(self, *, guild_id: int, violation_name: str = "default", user_id: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$inc": {f"violations.{violation_name}.{user_id}": -1}},
            upsert=True,
        )

        key = RedisKeys.GUILD_MEMBER_VIOLATION_COUNT.format(guild_id=guild_id, user_id=user_id, violation_name=violation_name)
        await self.redis_client.decr(key)

    async def set_violation_count(self, *, guild_id: int, violation_name: str = "default", user_id: int, count: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"violations.{violation_name}.{user_id}": count}},
            upsert=True,
        )

        key = RedisKeys.GUILD_MEMBER_VIOLATION_COUNT.format(guild_id=guild_id, user_id=user_id, violation_name=violation_name)
        await self.redis_client.set(key, count)

    async def get_violation_count(self, *, guild_id: int, violation_name: str = "default", user_id: int) -> int:
        key = RedisKeys.GUILD_MEMBER_VIOLATION_COUNT.format(guild_id=guild_id, user_id=user_id, violation_name=violation_name)
        count = await self.redis_client.get(key)

        if count is not None:
            return int(count)

        guild_config = await self.guilds_collection.find_one({"_id": guild_id, "violations": {"$exists": True}}, {"violations": 1})
        if guild_config is None:
            return 0

        violations = guild_config["violations"]
        count = violations.get(violation_name, {}).get(str(user_id), 0)

        await self.redis_client.set(key, count)
        return count


_GuildVoilationMixin = _GuildViolationMixin
