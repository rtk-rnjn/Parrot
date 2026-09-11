from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration


class _GuildTelephoneMixin:
    """Guild command prefix operations."""

    redis_client: Redis  # decode = True
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def is_telephone_enabled(self, *, guild_id: int) -> bool:
        redis_key = RedisKeys.GUILD_TELEPHONE_CONFIG_ENABLED.format(guild_id=guild_id)

        cached = await self.redis_client.get(redis_key)
        if cached is not None:
            return bool(int(cached))

        guild_config = await self.guilds_collection.find_one(
            {"_id": guild_id, "telephone_config.enabled": {"$exists": True}}, {"telephone_config.enabled": 1}
        )
        if guild_config is None:
            return False

        enabled = guild_config["telephone_config"]["enabled"]
        _ = await self.redis_client.set(redis_key, enabled)
        return enabled

    async def enable_telephone(self, *, guild_id: int) -> None:
        redis_key = RedisKeys.GUILD_TELEPHONE_CONFIG_ENABLED.format(guild_id=guild_id)

        _ = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {"telephone_config.enabled": True}},
            upsert=True,
        )

        _ = await self.redis_client.set(redis_key, True)

    async def disable_telephone(self, *, guild_id: int) -> None:
        redis_key = RedisKeys.GUILD_TELEPHONE_CONFIG_ENABLED.format(guild_id=guild_id)

        _ = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {"telephone_config.enabled": False}},
            upsert=True,
        )
        _ = await self.redis_client.set(redis_key, False)

    async def telephone_config_get_blocked_servers(self, *, guild_id: int) -> list[int]:
        redis_key = RedisKeys.GUILD_TELEPHONE_CONFIG_BLOCKED_SERVERS.format(guild_id=guild_id)

        cached = await self.redis_client.smembers(redis_key)
        if cached is not None:
            return [int(server_id) for server_id in cached]

        guild_config = await self.guilds_collection.find_one({"_id": guild_id}, {"telephone_config.blocked_servers": 1})
        if guild_config is None:
            return []

        blocked_servers = guild_config.get("telephone_config", {}).get("blocked_servers", [])
        if blocked_servers:
            _ = await self.redis_client.sadd(redis_key, *blocked_servers)
        return blocked_servers

    async def telephone_config_add_blocked_server(self, *, guild_id: int, server_id: int) -> None:
        redis_key = RedisKeys.GUILD_TELEPHONE_CONFIG_BLOCKED_SERVERS.format(guild_id=guild_id)

        _ = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$addToSet": {"telephone_config.blocked_servers": server_id}},
            upsert=True,
        )

        _ = await self.redis_client.sadd(redis_key, server_id)

    async def telephone_config_remove_blocked_server(self, *, guild_id: int, server_id: int) -> None:
        redis_key = RedisKeys.GUILD_TELEPHONE_CONFIG_BLOCKED_SERVERS.format(guild_id=guild_id)

        _ = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$pull": {"telephone_config.blocked_servers": server_id}},
            upsert=True,
        )

        _ = await self.redis_client.srem(redis_key, server_id)

    async def set_telephone_line_busy(self, *, guild_id: int, busy: bool) -> None:
        redis_key = RedisKeys.GUILD_TELEPHONE_LINE_BUSY.format(guild_id=guild_id)
        _ = await self.redis_client.set(redis_key, busy)

    async def is_telephone_line_busy(self, *, guild_id: int) -> bool:
        redis_key = RedisKeys.GUILD_TELEPHONE_LINE_BUSY.format(guild_id=guild_id)

        cached = await self.redis_client.get(redis_key)
        return bool(int(cached)) if cached is not None else False

    async def clear_telephone_line_busy(self, *, guild_id: int) -> None:
        redis_key = RedisKeys.GUILD_TELEPHONE_LINE_BUSY.format(guild_id=guild_id)
        _ = await self.redis_client.delete(redis_key)
