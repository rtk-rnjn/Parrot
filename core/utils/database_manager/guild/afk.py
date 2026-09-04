from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration


class _GuildAfkMixin:
    """Guild command prefix operations."""

    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def set_user_as_afk(self, *, guild_id: int, user_id: int, reason: str) -> None:
        afk_users_key = RedisKeys.GUILD_AFK_USERS.format(guild_id=guild_id)
        afk_user_reason_key = RedisKeys.GUILD_AFK_USER_REASON.format(guild_id=guild_id, user_id=user_id)

        await self.redis_client.sadd(afk_users_key, user_id)
        await self.redis_client.set(afk_user_reason_key, reason)

        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"afk_users.{user_id}": reason}},
            upsert=True,
        )

    async def remove_user_from_afk(self, *, guild_id: int, user_id: int) -> None:
        afk_users_key = RedisKeys.GUILD_AFK_USERS.format(guild_id=guild_id)
        afk_user_reason_key = RedisKeys.GUILD_AFK_USER_REASON.format(guild_id=guild_id, user_id=user_id)

        await self.redis_client.srem(afk_users_key, user_id)
        await self.redis_client.delete(afk_user_reason_key)

        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$unset": {f"afk_users.{user_id}": ""}},
            upsert=True,
        )

    async def is_user_afk(self, *, guild_id: int, user_id: int) -> bool:
        afk_users_key = RedisKeys.GUILD_AFK_USERS.format(guild_id=guild_id)
        maybe_afk = await self.redis_client.sismember(afk_users_key, str(user_id))
        if maybe_afk:
            return True

        data = await self.guilds_collection.find_one({"_id": guild_id, f"afk_users.{user_id}": {"$exists": True}})
        if data is not None:
            await self.redis_client.sadd(afk_users_key, user_id)
            await self.redis_client.set(
                RedisKeys.GUILD_AFK_USER_REASON.format(guild_id=guild_id, user_id=user_id),
                data["afk_users"][str(user_id)],
            )
            return True

        return data is not None

    async def get_afk_users(self, *, guild_id: int) -> dict[int, str]:
        afk_users_key = RedisKeys.GUILD_AFK_USERS.format(guild_id=guild_id)
        afk_user_ids = await self.redis_client.smembers(afk_users_key)

        if afk_user_ids:
            afk_users = {}
            for user_id in afk_user_ids:
                reason = await self.redis_client.get(
                    RedisKeys.GUILD_AFK_USER_REASON.format(guild_id=guild_id, user_id=user_id),
                )
                if reason is not None:
                    afk_users[int(user_id)] = reason
            return afk_users

        data = await self.guilds_collection.find_one({"_id": guild_id, "afk_users": {"$exists": True}}, {"afk_users": 1})
        if data is not None:
            for user_id, reason in data["afk_users"].items():
                await self.redis_client.sadd(afk_users_key, user_id)
                await self.redis_client.set(
                    RedisKeys.GUILD_AFK_USER_REASON.format(guild_id=guild_id, user_id=user_id),
                    reason,
                )
            return {int(user_id): reason for user_id, reason in data["afk_users"].items()}

        return {}

    async def get_afk_reason(self, *, guild_id: int, user_id: int) -> str | None:
        afk_user_reason_key = RedisKeys.GUILD_AFK_USER_REASON.format(guild_id=guild_id, user_id=user_id)
        reason = await self.redis_client.get(afk_user_reason_key)
        if reason is not None and isinstance(reason, str):
            return reason

        data = await self.guilds_collection.find_one(
            {"_id": guild_id, f"afk_users.{user_id}": {"$exists": True}},
            {f"afk_users.{user_id}": 1},
        )
        if data is not None:
            reason = data["afk_users"][str(user_id)]
            await self.redis_client.set(afk_user_reason_key, reason)
            return reason

        return None
