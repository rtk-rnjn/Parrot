from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration


class _GuildHubMixin:
    """Guild command prefix operations."""

    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def get_hub_channel_id(self, *, guild_id: int) -> int | None:
        redis_key = RedisKeys.GUILD_HUB_CHANNEL_ID.format(guild_id=guild_id)

        cached = await self.redis_client.get(redis_key)
        if cached is not None and isinstance(cached, int):
            return cached

        guild_config = await self.guilds_collection.find_one({"_id": guild_id, "hub_channel_id": {"$exists": True}}, {"hub_channel_id": 1})
        if guild_config is None:
            return None

        hub_channel_id = guild_config["hub_channel_id"]
        if hub_channel_id is not None:
            _ = await self.redis_client.set(redis_key, hub_channel_id)
        return hub_channel_id

    async def set_hub_channel_id(self, *, guild_id: int, hub_channel_id: int | None) -> None:
        redis_key = RedisKeys.GUILD_HUB_CHANNEL_ID.format(guild_id=guild_id)

        if hub_channel_id is None:
            await self.redis_client.delete(redis_key)
            await self.guilds_collection.update_one({"_id": guild_id}, {"$unset": {"hub_channel_id": ""}})
        else:
            await self.guilds_collection.update_one({"_id": guild_id}, {"$set": {"hub_channel_id": hub_channel_id}}, upsert=True)
            await self.redis_client.set(redis_key, hub_channel_id)

    async def set_hub_channel_owner_id(self, *, guild_id: int, channel_id: int, owner_id: int) -> None:
        redis_key = RedisKeys.GUILD_HUB_CHANNEL_OWNER.format(guild_id=guild_id, channel_id=channel_id)
        await self.guilds_collection.update_one({"_id": guild_id}, {"$set": {f"hub_channel_owners.{channel_id}": owner_id}}, upsert=True)
        await self.redis_client.set(redis_key, owner_id)

    async def get_hub_channel_owner_id(self, *, guild_id: int, channel_id: int) -> int | None:
        redis_key = RedisKeys.GUILD_HUB_CHANNEL_OWNER.format(guild_id=guild_id, channel_id=channel_id)

        cached = await self.redis_client.get(redis_key)
        if cached is not None and isinstance(cached, int):
            return cached

        guild_config = await self.guilds_collection.find_one(
            {"_id": guild_id, f"hub_channel_owners.{channel_id}": {"$exists": True}},
            {f"hub_channel_owners.{channel_id}": 1},
        )
        if guild_config is None:
            return None

        owner_id = guild_config.get("hub_channel_owners", {}).get(str(channel_id))
        if owner_id is not None:
            _ = await self.redis_client.set(redis_key, owner_id)
        return owner_id

    async def remove_hub_channel_owner_id(self, *, guild_id: int, channel_id: int) -> None:
        redis_key = RedisKeys.GUILD_HUB_CHANNEL_OWNER.format(guild_id=guild_id, channel_id=channel_id)
        await self.guilds_collection.update_one({"_id": guild_id}, {"$unset": {f"hub_channel_owners.{channel_id}": ""}})
        await self.redis_client.delete(redis_key)
