from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import UserConfiguration


class _UserHighlightsMixin:
    """User timezone operations."""

    redis_client: Redis
    users_collection: AsyncCollection[UserConfiguration]

    async def get_user_highlights(self, *, guild_id: int, user_id: int) -> set[str] | None:
        redis_key = RedisKeys.USER_HIGHLIGHT_WORDS.format(guild_id=guild_id, user_id=user_id)

        cached = await self.redis_client.smembers(redis_key)
        if cached:
            return cached  # type: ignore

        user_config = await self.users_collection.find_one(
            {"_id": user_id, "highlights.guild_id": guild_id},
            {"highlights.$": 1},
        )
        if not user_config:
            return None

        highlight = user_config["highlights"][0]
        await self.redis_client.sadd(redis_key, *highlight["words"])
        return set(highlight["words"])

    async def get_user_highlight_ignored_users(self, *, user_id: int) -> set[int] | None:
        redis_key = RedisKeys.USER_HIGHLIGHT_IGNORED_USERS.format(user_id=user_id)

        cached = await self.redis_client.smembers(redis_key)
        if cached:
            return {int(user) for user in cached}

        user_config = await self.users_collection.find_one(
            {
                "_id": user_id,
                "highlight_ignored_users": {"$exists": True},
            },
            {"highlight_ignored_users": 1},
        )
        if not user_config:
            return None

        ignored_users = user_config["highlight_ignored_users"]
        if ignored_users:
            await self.redis_client.sadd(redis_key, *ignored_users)
        return set(ignored_users)

    async def add_user_highlight_ignored_user(self, *, user_id: int, ignored_user_id: int) -> None:
        redis_key = RedisKeys.USER_HIGHLIGHT_IGNORED_USERS.format(user_id=user_id)
        await self.redis_client.sadd(redis_key, ignored_user_id)
        await self.users_collection.update_one({"_id": user_id}, {"$addToSet": {"highlight_ignored_users": ignored_user_id}})

    async def remove_user_highlight_ignored_user(self, *, user_id: int, ignored_user_id: int) -> None:
        redis_key = RedisKeys.USER_HIGHLIGHT_IGNORED_USERS.format(user_id=user_id)
        await self.redis_client.srem(redis_key, ignored_user_id)
        await self.users_collection.update_one({"_id": user_id}, {"$pull": {"highlight_ignored_users": ignored_user_id}})

    async def clear_user_highlight_ignored_users(self, *, user_id: int) -> None:
        redis_key = RedisKeys.USER_HIGHLIGHT_IGNORED_USERS.format(user_id=user_id)
        await self.redis_client.delete(redis_key)
        await self.users_collection.update_one({"_id": user_id}, {"$set": {"highlight_ignored_users": []}})

    async def add_user_highlight(self, *, guild_id: int, user_id: int, words: list[str]) -> None:
        redis_key = RedisKeys.USER_HIGHLIGHT_WORDS.format(guild_id=guild_id, user_id=user_id)
        await self.redis_client.sadd(redis_key, *words)
        await self.users_collection.update_one(
            {"_id": user_id, "highlights.guild_id": guild_id},
            {
                "$addToSet": {"highlights.$.words": {"$each": words}},
            },
        )
