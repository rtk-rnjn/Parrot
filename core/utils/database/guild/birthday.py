from __future__ import annotations

from discord.utils import MISSING

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin


class _GuildBirthdayMixin(DatabaseMixin):
    async def is_birthday_config_enabled(self, guild_id: int, /) -> bool:
        key = RedisKeys.GUILD_BIRTHDAY_CONFIG_ENABLED.format(guild_id=guild_id)
        cached = await self.redis_client.get(key)
        if cached is not None:
            return bool(int(cached))

        guild = await self.guilds_collection.find_one({"_id": guild_id, "birthday_config.enabled": {"$exists": True}}, {"birthday_config.enabled": 1})
        if guild is None:
            return False
        enabled = bool(guild["birthday_config"]["enabled"])
        await self.redis_client.set(key, int(enabled))
        return enabled

    async def get_birthday_config_channel_id(self, guild_id: int, /) -> int | None:
        key = RedisKeys.GUILD_BIRTHDAY_CONFIG_CHANNEL_ID.format(guild_id=guild_id)
        cached = await self.redis_client.get(key)
        if cached is not None:
            return int(cached)

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "birthday_config.channel_id": {"$exists": True}},
            {"birthday_config.channel_id": 1},
        )
        if guild is None:
            return None
        channel_id = guild["birthday_config"]["channel_id"]
        if channel_id is not None:
            await self.redis_client.set(key, channel_id)
        return channel_id

    async def edit_birthday_config(
        self,
        *,
        guild_id: int,
        enabled: bool = MISSING,
        channel_id: int | None = MISSING,
    ) -> bool:
        updates = {f"birthday_config.{field}": value for field, value in (("enabled", enabled), ("channel_id", channel_id)) if value is not MISSING}
        if not updates:
            return False

        result = await self.guilds_collection.update_one({"_id": guild_id}, {"$set": updates}, upsert=True)
        if enabled is not MISSING:
            await self.redis_client.set(RedisKeys.GUILD_BIRTHDAY_CONFIG_ENABLED.format(guild_id=guild_id), int(enabled))
        if channel_id is not MISSING:
            key = RedisKeys.GUILD_BIRTHDAY_CONFIG_CHANNEL_ID.format(guild_id=guild_id)
            if channel_id is None:
                await self.redis_client.delete(key)
            else:
                await self.redis_client.set(key, channel_id)
        return result.matched_count > 0 or result.upserted_id is not None
