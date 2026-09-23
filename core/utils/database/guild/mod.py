from __future__ import annotations

from discord.utils import MISSING

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin


class _GuildModeratorMixin(DatabaseMixin):
    """Guild moderator configuration, backed by MongoDB and Redis."""

    async def get_moderator_role_ids(self, *, guild_id: int) -> list[int]:
        key = RedisKeys.GUILD_MODERATOR_CONFIG_MODERATOR_ROLE_IDS.format(guild_id=guild_id)
        role_ids = await self.redis_client.smembers(key)
        if role_ids:
            return [int(role_id) for role_id in role_ids]

        guild_config = await self.guilds_collection.find_one(
            {"_id": guild_id, "moderator_config": {"$exists": True}}, {"moderator_config.moderator_role_ids": 1}
        )
        if guild_config is None:
            return []

        role_ids = guild_config["moderator_config"]["moderator_role_ids"]
        if role_ids:
            await self.redis_client.sadd(key, *role_ids)

        return role_ids

    async def get_moderator_logs_channel_id(self, *, guild_id: int) -> int | None:
        key = RedisKeys.GUILD_MODERATOR_CONFIG_MODERATOR_LOGS_CHANNEL_ID.format(guild_id=guild_id)
        channel_id = await self.redis_client.get(key)
        if channel_id:
            return int(channel_id)

        guild_config = await self.guilds_collection.find_one(
            {"_id": guild_id, "moderator_config": {"$exists": True}}, {"moderator_config.moderator_logs_channel_id": 1}
        )
        if guild_config is None:
            return None

        channel_id = guild_config["moderator_config"]["moderator_logs_channel_id"]
        if channel_id:
            await self.redis_client.set(key, channel_id)

        return channel_id

    async def edit_moderator_config(
        self,
        *,
        guild_id: int,
        moderator_role_ids: list[int] | None = MISSING,
        moderator_logs_channel_id: int | None = MISSING,
    ) -> None:
        update_data = {}
        if moderator_role_ids is not MISSING:
            update_data["moderator_config.moderator_role_ids"] = moderator_role_ids
            key = RedisKeys.GUILD_MODERATOR_CONFIG_MODERATOR_ROLE_IDS.format(guild_id=guild_id)
            await self.redis_client.delete(key)

        if moderator_logs_channel_id is not MISSING:
            update_data["moderator_config.moderator_logs_channel_id"] = moderator_logs_channel_id
            key = RedisKeys.GUILD_MODERATOR_CONFIG_MODERATOR_LOGS_CHANNEL_ID.format(guild_id=guild_id)
            await self.redis_client.delete(key)

        if update_data:
            await self.guilds_collection.update_one({"_id": guild_id}, {"$set": update_data}, upsert=True)

    async def add_moderator_role(self, *, guild_id: int, role_id: int) -> None:
        await self.guilds_collection.update_one({"_id": guild_id}, {"$addToSet": {"moderator_config.moderator_role_ids": role_id}}, upsert=True)

        key = RedisKeys.GUILD_MODERATOR_CONFIG_MODERATOR_ROLE_IDS.format(guild_id=guild_id)
        await self.redis_client.sadd(key, role_id)

    async def remove_moderator_role(self, *, guild_id: int, role_id: int) -> None:
        await self.guilds_collection.update_one({"_id": guild_id}, {"$pull": {"moderator_config.moderator_role_ids": role_id}}, upsert=True)

        key = RedisKeys.GUILD_MODERATOR_CONFIG_MODERATOR_ROLE_IDS.format(guild_id=guild_id)
        await self.redis_client.srem(key, role_id)
