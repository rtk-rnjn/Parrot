from __future__ import annotations

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin


class _GuildViolationMixin(DatabaseMixin):
    """Guild violation counters, backed by MongoDB and Redis."""

    async def increase_violation(self, *, guild_id: int, violation_name: str = "default", user_id: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$inc": {f"violations.{violation_name}.{user_id}": 1}},
            upsert=True,
        )

        key = RedisKeys.GUILD_MEMBER_VIOLATION_COUNT.format(guild_id=guild_id, user_id=user_id, violation_name=violation_name)
        await self.redis_client.incr(key)

    async def reset_violation(self, *, guild_id: int, violation_name: str = "default", user_id: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"violations.{violation_name}.{user_id}": 0}},
            upsert=True,
        )

        key = RedisKeys.GUILD_MEMBER_VIOLATION_COUNT.format(guild_id=guild_id, user_id=user_id, violation_name=violation_name)
        await self.redis_client.set(key, 0)

    async def decrease_violation(self, *, guild_id: int, violation_name: str = "default", user_id: int) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$inc": {f"violations.{violation_name}.{user_id}": -1}},
            upsert=True,
        )

        key = RedisKeys.GUILD_MEMBER_VIOLATION_COUNT.format(guild_id=guild_id, user_id=user_id, violation_name=violation_name)
        await self.redis_client.decr(key)

    async def set_violation_count(
        self,
        *,
        guild_id: int,
        violation_name: str = "default",
        user_id: int,
        count: int,
    ) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"violations.{violation_name}.{user_id}": count}},
            upsert=True,
        )

        key = RedisKeys.GUILD_MEMBER_VIOLATION_COUNT.format(guild_id=guild_id, user_id=user_id, violation_name=violation_name)
        await self.redis_client.set(key, count)

    async def get_violation_count(self, *, guild_id: int, violation_name: str = "default", user_id: int) -> int:
        key = RedisKeys.GUILD_MEMBER_VIOLATION_COUNT.format(guild_id=guild_id, user_id=user_id, violation_name=violation_name)
        count = await self.redis_client.get(key)

        if count is not None:
            return int(count)

        guild_config = await self.guilds_collection.find_one({"_id": guild_id, "violations": {"$exists": True}}, {"violations": 1})
        if guild_config is None:
            return 0

        violations = guild_config["violations"]
        count = violations.get(violation_name, {}).get(str(user_id), 0)

        await self.redis_client.set(key, count)
        return count

    async def get_all_user_violations(self, *, guild_id: int, user_id: int) -> dict[str, int]:
        guild_config = await self.guilds_collection.find_one({"_id": guild_id, "violations": {"$exists": True}}, {"violations": 1})
        if guild_config is None:
            return {}

        violations = guild_config["violations"]
        user_violations = {violation_name: counts.get(str(user_id), 0) for violation_name, counts in violations.items()}

        # Update Redis cache for each violation
        for violation_name, count in user_violations.items():
            key = RedisKeys.GUILD_MEMBER_VIOLATION_COUNT.format(guild_id=guild_id, user_id=user_id, violation_name=violation_name)
            await self.redis_client.set(key, count)

        return user_violations

    async def set_default_violation_expiration(self, *, guild_id: int, expiration_seconds: int | None) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {"default_violation_expiration": expiration_seconds}},
            upsert=True,
        )

        key = RedisKeys.GUILD_DEFAULT_VIOLATION_EXPIRATION.format(guild_id=guild_id)
        if expiration_seconds is not None:
            await self.redis_client.set(key, expiration_seconds)
        else:
            await self.redis_client.delete(key)

    async def get_default_violation_expiration(self, *, guild_id: int) -> int | None:
        key = RedisKeys.GUILD_DEFAULT_VIOLATION_EXPIRATION.format(guild_id=guild_id)
        expiration = await self.redis_client.get(key)

        if expiration is not None:
            return int(expiration)

        guild_config = await self.guilds_collection.find_one({"_id": guild_id}, {"default_violation_expiration": 1})
        if guild_config is None:
            return None

        expiration = guild_config.get("default_violation_expiration")
        if expiration is not None:
            await self.redis_client.set(key, expiration)

        return expiration
