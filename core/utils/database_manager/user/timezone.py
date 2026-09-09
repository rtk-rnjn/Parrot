from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import UserConfiguration


class _UserTimezoneMixin:
    """User timezone operations."""

    redis_client: Redis
    users_collection: AsyncCollection[UserConfiguration]

    async def get_user_timezone(self, user_id: int, /) -> str | None:
        redis_key = RedisKeys.USER_TIMEZONE.format(user_id=user_id)

        cached = await self.redis_client.get(redis_key)
        if cached is not None and isinstance(cached, str):
            return cached

        user_config = await self.users_collection.find_one({"_id": user_id, "timezone": {"$exists": True}}, {"timezone": 1})
        if user_config is None:
            return None

        timezone = user_config["timezone"]
        _ = await self.redis_client.set(redis_key, timezone)
        return timezone

    async def set_user_timezone(self, *, user_id: int, timezone: str) -> None:
        redis_key = RedisKeys.USER_TIMEZONE.format(user_id=user_id)

        _ = await self.users_collection.update_one(
            {"_id": user_id},
            {"$set": {"timezone": timezone}},
            upsert=True,
        )

        _ = await self.redis_client.set(redis_key, timezone)
