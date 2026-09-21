from __future__ import annotations

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin


class _GuildSuggestionMixin(DatabaseMixin):
    """Guild suggestion channel operations."""

    async def get_suggestion_channel_id(self, *, guild_id: int) -> int | None:
        redis_key = RedisKeys.GUILD_SUGGESTION_CHANNEL_ID.format(guild_id=guild_id)

        cached = await self.redis_client.get(redis_key)
        if cached is not None and isinstance(cached, int):
            return cached

        guild_config = await self.guilds_collection.find_one(
            {"_id": guild_id, "suggestion_channel_id": {"$exists": True, "$ne": None}},
            {"suggestion_channel_id": 1},
        )
        if guild_config is None:
            return None

        suggestion_channel_id = guild_config["suggestion_channel_id"]
        if suggestion_channel_id is not None:
            await self.redis_client.set(redis_key, suggestion_channel_id)
        return suggestion_channel_id

    async def edit_suggestion_config(self, *, guild_id: int, suggestion_channel_id: int | None) -> None:
        redis_key = RedisKeys.GUILD_SUGGESTION_CHANNEL_ID.format(guild_id=guild_id)

        if suggestion_channel_id is None:
            await self.redis_client.delete(redis_key)
            await self.guilds_collection.update_one({"_id": guild_id}, {"$set": {"suggestion_channel_id": None}}, upsert=True)
        else:
            await self.guilds_collection.update_one({"_id": guild_id}, {"$set": {"suggestion_channel_id": suggestion_channel_id}}, upsert=True)
            await self.redis_client.set(redis_key, suggestion_channel_id)
