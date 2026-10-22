from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin
from ..models import UserConfiguration

CACHE_TTL = 3600


class _UserHighlightsMixin(DatabaseMixin):
    """User highlight operations."""

    users_collection: AsyncCollection[UserConfiguration]

    async def _fill_cache(self, key: str, values: set[str] | set[int]) -> None:
        if not values:
            return
        await self.redis_client.sadd(key, *values)
        await self.redis_client.expire(key, CACHE_TTL)

    async def get_user_highlights(self, *, guild_id: int, user_id: int) -> set[str] | None:
        redis_key = RedisKeys.USER_HIGHLIGHT_WORDS.format(guild_id=guild_id, user_id=user_id)

        cached = await self.redis_client.smembers(redis_key)
        if cached:
            return {item.decode() if isinstance(item, bytes) else item for item in cached}

        user_config = await self.users_collection.find_one({"_id": user_id, "highlights.guild_id": guild_id}, {"highlights.$": 1})
        if not user_config:
            return None

        words = set(user_config["highlights"][0]["words"])
        await self._fill_cache(redis_key, words)
        return words

    async def get_user_highlights_by_guild(self, *, user_id: int) -> dict[int, set[str]]:
        user_config = await self.users_collection.find_one({"_id": user_id}, {"highlights": 1})
        if not user_config:
            return {}
        return {entry["guild_id"]: set(entry["words"]) for entry in user_config.get("highlights", []) if entry["words"]}

    async def get_guild_highlights(self, *, guild_id: int) -> dict[int, set[str]]:
        result: dict[int, set[str]] = {}

        async for user_config in self.users_collection.find({"highlights.guild_id": guild_id}, {"_id": 1, "highlights.$": 1}):
            words = set(user_config["highlights"][0]["words"])
            if words:
                result[user_config["_id"]] = words

        return result

    async def add_user_highlight(self, *, guild_id: int, user_id: int, words: list[str]) -> None:
        words = list(dict.fromkeys(words))
        if not words:
            return

        existing_filter = {"_id": user_id, "highlights.guild_id": guild_id}
        existing_update = {"$addToSet": {"highlights.$.words": {"$each": words}}}

        result = await self.users_collection.update_one(existing_filter, existing_update)
        if result.matched_count == 0:
            try:
                await self.users_collection.update_one(
                    {"_id": user_id, "highlights.guild_id": {"$ne": guild_id}},
                    {"$push": {"highlights": {"guild_id": guild_id, "words": words}}},
                    upsert=True,
                )
            except DuplicateKeyError:
                await self.users_collection.update_one(existing_filter, existing_update)

        await self.redis_client.delete(RedisKeys.USER_HIGHLIGHT_WORDS.format(guild_id=guild_id, user_id=user_id))

    async def remove_user_highlight(self, *, guild_id: int, user_id: int, words: list[str]) -> None:
        if not words:
            return

        await self.users_collection.update_one(
            {"_id": user_id, "highlights.guild_id": guild_id},
            {"$pull": {"highlights.$.words": {"$in": words}}},
        )
        await self.redis_client.delete(RedisKeys.USER_HIGHLIGHT_WORDS.format(guild_id=guild_id, user_id=user_id))

    async def get_user_highlight_ignored_users(self, *, user_id: int) -> set[int]:
        redis_key = RedisKeys.USER_HIGHLIGHT_IGNORED_USERS.format(user_id=user_id)

        cached = await self.redis_client.smembers(redis_key)
        if cached:
            return {int(user) for user in cached}

        user_config = await self.users_collection.find_one({"_id": user_id}, {"highlight_ignored_users": 1})
        ignored = set(user_config.get("highlight_ignored_users", [])) if user_config else set()
        await self._fill_cache(redis_key, ignored)
        return ignored

    async def add_user_highlight_ignored_user(self, *, user_id: int, ignored_user_id: int) -> None:
        await self.users_collection.update_one(
            {"_id": user_id},
            {"$addToSet": {"highlight_ignored_users": ignored_user_id}},
            upsert=True,
        )
        await self.redis_client.delete(RedisKeys.USER_HIGHLIGHT_IGNORED_USERS.format(user_id=user_id))

    async def remove_user_highlight_ignored_user(self, *, user_id: int, ignored_user_id: int) -> None:
        await self.users_collection.update_one({"_id": user_id}, {"$pull": {"highlight_ignored_users": ignored_user_id}})
        await self.redis_client.delete(RedisKeys.USER_HIGHLIGHT_IGNORED_USERS.format(user_id=user_id))

    async def clear_user_highlight_ignored_users(self, *, user_id: int) -> None:
        await self.users_collection.update_one({"_id": user_id}, {"$set": {"highlight_ignored_users": []}})
        await self.redis_client.delete(RedisKeys.USER_HIGHLIGHT_IGNORED_USERS.format(user_id=user_id))
