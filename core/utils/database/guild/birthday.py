from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import BirthdayConfig, GuildConfiguration

_MISSING = object()


class _GuildBirthdayMixin:
    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def edit_birthday_config(
        self,
        *,
        guild_id: int,
        enabled: bool | object = _MISSING,
        channel_id: int | None | object = _MISSING,
    ) -> bool:
        updates = {f"birthday_config.{field}": value for field, value in (("enabled", enabled), ("channel_id", channel_id)) if value is not _MISSING}
        if not updates:
            return False

        result = await self.guilds_collection.update_one({"_id": guild_id}, {"$set": updates}, upsert=True)
        await self.redis_client.delete(RedisKeys.GUILD_BIRTHDAY_CONFIG.format(guild_id=guild_id))
        return result.matched_count > 0 or result.upserted_id is not None

    async def get_birthday_config(self, guild_id: int, /) -> BirthdayConfig | None:
        cache_key = RedisKeys.GUILD_BIRTHDAY_CONFIG.format(guild_id=guild_id)
        cached = await self.redis_client.hgetall(cache_key)
        if cached:
            return {"enabled": cached["enabled"] == "1", "channel_id": int(cached["channel_id"]) if cached.get("channel_id") else None}

        guild = await self.guilds_collection.find_one({"_id": guild_id, "birthday_config": {"$exists": True}}, {"birthday_config": 1})
        if guild is None:
            return None

        config: BirthdayConfig = {
            "enabled": bool(guild["birthday_config"].get("enabled", False)),
            "channel_id": guild["birthday_config"].get("channel_id"),
        }
        await self.redis_client.hset(cache_key, mapping={"enabled": int(config["enabled"]), "channel_id": config["channel_id"] or ""})
        return config
