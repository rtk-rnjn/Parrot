from __future__ import annotations

from collections.abc import Mapping

from discord.utils import MISSING
from pymongo import UpdateOne
from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration, LevelingConfig


class _GuildLevelingMixin:
    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def _cache_leveling_config(self, *, guild_id: int, config: LevelingConfig) -> None:
        enabled_key = RedisKeys.GUILD_LEVELING_CONFIG_ENABLED.format(guild_id=guild_id)
        roles_key = RedisKeys.GUILD_LEVELING_CONFIG_LEVEL_ROLES.format(guild_id=guild_id)

        await self.redis_client.set(enabled_key, int(config["enabled"]))

        await self.redis_client.delete(roles_key)
        level_roles = config.get("level_roles", {})
        if level_roles:
            await self.redis_client.hset(roles_key, mapping={str(level): str(role_id) for level, role_id in level_roles.items()})

    async def _invalidate_leveling_config_cache(self, *, guild_id: int) -> None:
        await self.redis_client.delete(
            RedisKeys.GUILD_LEVELING_CONFIG_ENABLED.format(guild_id=guild_id),
            RedisKeys.GUILD_LEVELING_CONFIG_LEVEL_ROLES.format(guild_id=guild_id),
        )

    async def edit_leveling_config(  # noqa: PLR0913
        self,
        *,
        guild_id: int,
        enabled: bool = MISSING,
        level_roles: Mapping[int, int] = MISSING,
    ) -> bool:
        updates = {}
        if enabled is not MISSING:
            updates["leveling_config.enabled"] = enabled
        if level_roles is not MISSING:
            updates["leveling_config.level_roles"] = dict(level_roles)
        if not updates:
            return False
        result = await self.guilds_collection.update_one({"_id": guild_id, "leveling_config": {"$exists": True}}, {"$set": updates})
        if result.matched_count == 0:
            return False

        await self._invalidate_leveling_config_cache(guild_id=guild_id)
        return True

    async def is_leveling_enabled(self, guild_id: int, /) -> bool:
        enabled_key = RedisKeys.GUILD_LEVELING_CONFIG_ENABLED.format(guild_id=guild_id)
        enabled_value = await self.redis_client.get(enabled_key)
        if enabled_value is not None:
            return bool(int(enabled_value))

        guild_config = await self.guilds_collection.find_one(
            {"_id": guild_id, "leveling_config.enabled": {"$exists": True}},
            {"leveling_config.enabled": 1},
        )
        if guild_config is None or "leveling_config" not in guild_config:
            return False

        enabled = guild_config["leveling_config"].get("enabled", False)
        await self.redis_client.set(enabled_key, int(enabled))
        return enabled

    async def set_level_role(self, *, guild_id: int, level: int, role_id: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"leveling_config.level_roles.{level}": role_id}},
            upsert=True,
        )
        roles_key = RedisKeys.GUILD_LEVELING_CONFIG_LEVEL_ROLES.format(guild_id=guild_id)
        await self.redis_client.hset(roles_key, str(level), str(role_id))

    async def remove_level_role(self, *, guild_id: int, level: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$unset": {f"leveling_config.level_roles.{level}": ""}},
        )
        roles_key = RedisKeys.GUILD_LEVELING_CONFIG_LEVEL_ROLES.format(guild_id=guild_id)
        await self.redis_client.hdel(roles_key, str(level))

    async def get_level_role(self, *, guild_id: int, level: int) -> int | None:
        roles_key = RedisKeys.GUILD_LEVELING_CONFIG_LEVEL_ROLES.format(guild_id=guild_id)
        role_id = await self.redis_client.hget(roles_key, str(level))
        if role_id is not None:
            return int(role_id)

        guild_config = await self.guilds_collection.find_one(
            {"_id": guild_id, f"leveling_config.level_roles.{level}": {"$exists": True}},
            {f"leveling_config.level_roles.{level}": 1},
        )
        if guild_config is None or "leveling_config" not in guild_config:
            return None

        level_roles = guild_config["leveling_config"].get("level_roles", {})
        role_id = level_roles.get(str(level), 0)
        if role_id:
            await self.redis_client.hset(roles_key, str(level), str(role_id))
        return role_id

    async def incr_user_xp(self, *, guild_id: int, user_id: int, xp: int) -> None:
        key = RedisKeys.GUILD_LEVELING_DATA.format(guild_id=guild_id)
        await self.redis_client.hincrby(key, str(user_id), xp)

    async def flush_leveling_data(self, guild_id: int, /) -> int:
        """Persist accumulated Redis XP in one MongoDB bulk operation."""
        active_key = RedisKeys.GUILD_LEVELING_DATA.format(guild_id=guild_id)
        pending_key = f"{active_key}:pending"

        if not await self.redis_client.exists(pending_key):
            if not await self.redis_client.exists(active_key):
                return 0
            await self.redis_client.rename(active_key, pending_key)

        data = await self.redis_client.hgetall(pending_key)
        if not data:
            await self.redis_client.delete(pending_key)
            return 0

        operations = [
            UpdateOne(
                {"_id": guild_id},
                {"$inc": {f"leveling_data.{user_id}": int(xp)}},
                upsert=True,
            )
            for user_id, xp in data.items()
        ]
        await self.guilds_collection.bulk_write(operations, ordered=False)
        await self.redis_client.delete(pending_key)
        return len(operations)

    async def flush_all_leveling_data(self) -> int:
        """Persist accumulated XP for every guild with a Redis leveling hash."""
        guild_ids: set[int] = set()
        async for key in self.redis_client.scan_iter(match="guild:*:leveling_data*"):
            parts = key.split(":")
            if len(parts) >= 3 and parts[0] == "guild" and parts[2] == "leveling_data":
                guild_ids.add(int(parts[1]))

        flushed_users = 0
        for guild_id in guild_ids:
            flushed_users += await self.flush_leveling_data(guild_id)
        return flushed_users

    async def get_user_xp(self, *, guild_id: int, user_id: int) -> int | None:
        key = RedisKeys.GUILD_LEVELING_DATA.format(guild_id=guild_id)
        pending_key = f"{key}:pending"

        guild_config = await self.guilds_collection.find_one(
            {"_id": guild_id},
            {f"leveling_data.{user_id}": 1},
        )
        user_xp = (guild_config or {}).get("leveling_data", {}).get(str(user_id), 0)
        active_delta = await self.redis_client.hget(key, str(user_id))
        pending_delta = await self.redis_client.hget(pending_key, str(user_id))
        total_xp = user_xp + int(active_delta or 0) + int(pending_delta or 0)
        if guild_config is None and not active_delta and not pending_delta:
            return None
        return total_xp
