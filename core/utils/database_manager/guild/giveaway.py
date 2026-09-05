from __future__ import annotations

from discord.utils import MISSING
from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GiveawayConfig, GuildConfiguration


class _GuildGiveawayMixin:
    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def _cache_giveaway_config(self, *, guild_id: int, config: GiveawayConfig) -> None:
        key = RedisKeys.GUILD_GIVEAWAY_CONFIG_ENABLED.format(guild_id=guild_id)
        await self.redis_client.set(key, int(config["enabled"]))
        for key, field in (
            (RedisKeys.GUILD_GIVEAWAY_CONFIG_CHANNEL_ID, "giveaway_channel_id"),
            (RedisKeys.GUILD_GIVEAWAY_CONFIG_ROLE_ID, "giveaway_role_id"),
        ):
            value = config[field]
            redis_key = key.format(guild_id=guild_id)
            if value is None:
                await self.redis_client.delete(redis_key)
            else:
                await self.redis_client.set(redis_key, value)

    async def _invalidate_giveaway_config_cache(self, *, guild_id: int) -> None:
        await self.redis_client.delete(
            RedisKeys.GUILD_GIVEAWAY_CONFIG_ENABLED.format(guild_id=guild_id),
            RedisKeys.GUILD_GIVEAWAY_CONFIG_CHANNEL_ID.format(guild_id=guild_id),
            RedisKeys.GUILD_GIVEAWAY_CONFIG_ROLE_ID.format(guild_id=guild_id),
        )

    async def edit_giveaway_config(
        self,
        *,
        guild_id: int,
        enabled: bool = MISSING,
        giveaway_channel_id: int | None = MISSING,
        giveaway_role_id: int | None = MISSING,
    ) -> bool:
        updates = {}
        if enabled is not MISSING:
            updates["giveaway_config.enabled"] = enabled
        if giveaway_channel_id is not MISSING:
            updates["giveaway_config.giveaway_channel_id"] = giveaway_channel_id
        if giveaway_role_id is not MISSING:
            updates["giveaway_config.giveaway_role_id"] = giveaway_role_id

        if not updates:
            return False

        result = await self.guilds_collection.update_one({"_id": guild_id, "giveaway_config": {"$exists": True}}, {"$set": updates})
        if result.matched_count == 0:
            return False

        await self._invalidate_giveaway_config_cache(guild_id=guild_id)
        return True

    async def delete_giveaway_config(self, *, guild_id: int) -> bool:
        result = await self.guilds_collection.update_one({"_id": guild_id, "giveaway_config": {"$exists": True}}, {"$unset": {"giveaway_config": ""}})
        await self._invalidate_giveaway_config_cache(guild_id=guild_id)
        return result.modified_count > 0

    async def is_giveaway_config_enabled(self, guild_id: int, /) -> bool:
        key = RedisKeys.GUILD_GIVEAWAY_CONFIG_ENABLED.format(guild_id=guild_id)
        value = await self._get_int(key)
        if value is not None:
            return bool(value)

        config = await self.guilds_collection.find_one(
            {"_id": guild_id, "giveaway_config.enabled": {"$exists": True}},
            {"giveaway_config": 1},
        )
        if config is None:
            return False

        await self._cache_giveaway_config(guild_id=guild_id, config=config["giveaway_config"])
        return config["giveaway_config"]["enabled"]

    async def get_giveaway_channel_id(self, guild_id: int, /) -> int | None:
        key = RedisKeys.GUILD_GIVEAWAY_CONFIG_CHANNEL_ID.format(guild_id=guild_id)
        value = await self._get_int(key)
        if value is not None:
            return value

        config = await self.guilds_collection.find_one(
            {"_id": guild_id, "giveaway_config.giveaway_channel_id": {"$exists": True}},
            {"giveaway_config": 1},
        )
        if config is None:
            return None

        await self._cache_giveaway_config(guild_id=guild_id, config=config["giveaway_config"])
        return config["giveaway_config"]["giveaway_channel_id"]

    async def get_giveaway_role_id(self, guild_id: int, /) -> int | None:
        key = RedisKeys.GUILD_GIVEAWAY_CONFIG_ROLE_ID.format(guild_id=guild_id)
        value = await self._get_int(key)
        if value is not None:
            return value

        config = await self.guilds_collection.find_one(
            {"_id": guild_id, "giveaway_config.giveaway_role_id": {"$exists": True}},
            {"giveaway_config": 1},
        )
        if config is None:
            return None

        await self._cache_giveaway_config(guild_id=guild_id, config=config["giveaway_config"])
        return config["giveaway_config"]["giveaway_role_id"]

    async def _get_int(self, key: str) -> int | None:
        value = await self.redis_client.get(key)
        return int(value) if value is not None else None
