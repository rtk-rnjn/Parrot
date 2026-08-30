from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration


class _GuildMuteRoleMixin:
    """Guild mute-role operations."""

    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def set_guild_mute_role(self, *, guild_id: int, mute_role_id: int) -> None:
        _ = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {"mute_role_id": mute_role_id}},
            upsert=True,
        )

        redis_key = RedisKeys.GUILD_MUTE_ROLE_ID.format(guild_id=guild_id)
        _ = await self.redis_client.set(redis_key, mute_role_id, ex=3600)

    async def get_guild_mute_role(self, *, guild_id: int) -> int | None:
        redis_key = RedisKeys.GUILD_MUTE_ROLE_ID.format(guild_id=guild_id)

        cached = await self.redis_client.get(redis_key)
        if cached is not None:
            try:
                return int(cached)
            except ValueError:
                return None

        guild_config = await self.guilds_collection.find_one({"_id": guild_id})
        if guild_config is None:
            return None

        mute_role_id = guild_config.get("mute_role_id")
        if mute_role_id is not None:
            _ = await self.redis_client.set(redis_key, mute_role_id, ex=3600)

        return mute_role_id

    async def get_muted_members(self, *, guild_id: int) -> list[int]:
        redis_key = RedisKeys.GUILD_MUTED_MEMBERS.format(guild_id=guild_id)

        cached = await self.redis_client.smembers(redis_key)
        # smembers returns empty set for missing key; only trust cache when non-empty.
        if cached:
            try:
                return [int(member_id) for member_id in cached]
            except ValueError:
                return []

        guild_config = await self.guilds_collection.find_one({"_id": guild_id})
        if guild_config is None:
            return []

        muted_members = guild_config.get("muted_members", [])
        if muted_members:
            _ = await self.redis_client.sadd(redis_key, *muted_members)
            _ = await self.redis_client.expire(redis_key, 3600)

        return muted_members

    async def add_muted_member(self, *, guild_id: int, member_id: int) -> None:
        _ = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$addToSet": {"muted_members": member_id}},
            upsert=True,
        )

        redis_key = RedisKeys.GUILD_MUTED_MEMBERS.format(guild_id=guild_id)
        _ = await self.redis_client.sadd(redis_key, member_id)
        _ = await self.redis_client.expire(redis_key, 3600)

    async def remove_muted_member(self, *, guild_id: int, member_id: int) -> None:
        _ = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$pull": {"muted_members": member_id}},
            upsert=True,
        )

        redis_key = RedisKeys.GUILD_MUTED_MEMBERS.format(guild_id=guild_id)
        _ = await self.redis_client.srem(redis_key, member_id)

    async def remove_all_muted_members(self, *, guild_id: int) -> None:
        _ = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {"muted_members": []}},
            upsert=True,
        )

        redis_key = RedisKeys.GUILD_MUTED_MEMBERS.format(guild_id=guild_id)
        _ = await self.redis_client.delete(redis_key)

    async def get_all_muted_members(self):
        cursor = self.guilds_collection.find({"muted_members": {"$exists": True, "$ne": []}})
        async for guild_config in cursor:
            yield guild_config["_id"], guild_config["muted_members"]

    async def delete_mute_role(self, *, guild_id: int) -> None:
        """Delete mute role and clear muted-member list for the guild."""
        _ = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {"mute_role_id": None}},
            upsert=True,
        )

        redis_key = RedisKeys.GUILD_MUTE_ROLE_ID.format(guild_id=guild_id)
        _ = await self.redis_client.delete(redis_key)

        await self.remove_all_muted_members(guild_id=guild_id)
