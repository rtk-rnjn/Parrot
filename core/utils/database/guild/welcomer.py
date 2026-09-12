from __future__ import annotations

from discord.utils import MISSING
from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration, WelcomeConfig


class _GuildWelcomerMixin:
    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def _cache_welcome_config(self, *, guild_id: int, config: WelcomeConfig) -> None:
        values = {
            RedisKeys.GUILD_WELCOME_CONFIG_ENABLED: int(config["enabled"]),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_MESSAGE: config["on_member_join_message"],
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_CHANNEL_ID: config["on_member_join_channel_id"],
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_MESSAGE: config["on_member_leave_message"],
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_CHANNEL_ID: config["on_member_leave_channel_id"],
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_ROLE_ID: config["on_member_join_role_id"],
        }
        for key, value in values.items():
            redis_key = key.format(guild_id=guild_id)
            if value is None:
                await self.redis_client.delete(redis_key)
            else:
                await self.redis_client.set(redis_key, value)

    async def _invalidate_welcome_config_cache(self, *, guild_id: int) -> None:
        await self.redis_client.delete(
            RedisKeys.GUILD_WELCOME_CONFIG_ENABLED.format(guild_id=guild_id),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_MESSAGE.format(guild_id=guild_id),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_CHANNEL_ID.format(guild_id=guild_id),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_MESSAGE.format(guild_id=guild_id),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_CHANNEL_ID.format(guild_id=guild_id),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_ROLE_ID.format(guild_id=guild_id),
        )

    async def edit_welcome_config(  # noqa: PLR0913
        self,
        *,
        guild_id: int,
        enabled: bool = MISSING,
        on_member_join_message: str | None = MISSING,
        on_member_join_channel_id: int | None = MISSING,
        on_member_join_role_id: int | None = MISSING,
        on_member_leave_message: str | None = MISSING,
        on_member_leave_channel_id: int | None = MISSING,
    ) -> bool:
        updates = {}
        for field, value in (
            ("enabled", enabled),
            ("on_member_join_message", on_member_join_message),
            ("on_member_join_channel_id", on_member_join_channel_id),
            ("on_member_join_role_id", on_member_join_role_id),
            ("on_member_leave_message", on_member_leave_message),
            ("on_member_leave_channel_id", on_member_leave_channel_id),
        ):
            if value is not MISSING:
                updates[f"welcome_config.{field}"] = value

        if not updates:
            return False

        result = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": updates},
        )
        if result.matched_count == 0:
            return False

        await self._invalidate_welcome_config_cache(guild_id=guild_id)
        return True

    async def delete_welcome_config(self, *, guild_id: int) -> bool:
        result = await self.guilds_collection.update_one(
            {"_id": guild_id, "welcome_config": {"$exists": True}},
            {"$unset": {"welcome_config": ""}},
        )
        await self._invalidate_welcome_config_cache(guild_id=guild_id)
        return result.modified_count > 0

    async def is_welcome_enabled(self, guild_id: int, /) -> bool:
        key = RedisKeys.GUILD_WELCOME_CONFIG_ENABLED.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            return bool(int(value))

        config = await self.guilds_collection.find_one(
            {"_id": guild_id, "welcome_config.enabled": {"$exists": True}},
            {"welcome_config": 1},
        )
        if config is None:
            return False

        welcome_config = config["welcome_config"]
        await self._cache_welcome_config(guild_id=guild_id, config=welcome_config)
        return welcome_config["enabled"]

    async def get_welcome_join_message(self, guild_id: int, /) -> str | None:
        key = RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_MESSAGE.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            return value if isinstance(value, str) else value.decode()

        return await self._get_welcome_config_value(
            guild_id=guild_id,
            field="on_member_join_message",
            query_field="welcome_config.on_member_join_message",
        )

    async def get_welcome_join_channel_id(self, guild_id: int, /) -> int | None:
        key = RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_CHANNEL_ID.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            return int(value)

        return await self._get_welcome_config_value(
            guild_id=guild_id,
            field="on_member_join_channel_id",
            query_field="welcome_config.on_member_join_channel_id",
        )

    async def get_welcome_leave_message(self, guild_id: int, /) -> str | None:
        key = RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_MESSAGE.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            return value if isinstance(value, str) else value.decode()

        return await self._get_welcome_config_value(
            guild_id=guild_id,
            field="on_member_leave_message",
            query_field="welcome_config.on_member_leave_message",
        )

    async def get_welcome_leave_channel_id(self, guild_id: int, /) -> int | None:
        key = RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_CHANNEL_ID.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            return int(value)

        return await self._get_welcome_config_value(
            guild_id=guild_id,
            field="on_member_leave_channel_id",
            query_field="welcome_config.on_member_leave_channel_id",
        )

    async def _get_welcome_config_value(self, *, guild_id: int, field: str, query_field: str):
        config = await self.guilds_collection.find_one(
            {"_id": guild_id, query_field: {"$exists": True}},
            {"welcome_config": 1},
        )
        if config is None:
            return None

        welcome_config = config["welcome_config"]
        await self._cache_welcome_config(guild_id=guild_id, config=welcome_config)
        return welcome_config.get(field)

    async def get_welcome_join_role_id(self, guild_id: int, /) -> int | None:
        key = RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_ROLE_ID.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            return int(value)

        return await self._get_welcome_config_value(
            guild_id=guild_id,
            field="on_member_join_role_id",
            query_field="welcome_config.on_member_join_role_id",
        )

    async def set_welcome_join_role_id(self, guild_id: int, role_id: int | None, /) -> bool:
        updated = await self.edit_welcome_config(guild_id=guild_id, on_member_join_role_id=role_id)
        if updated:
            await self.redis_client.set(
                RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_ROLE_ID.format(guild_id=guild_id),
                role_id if role_id is not None else "",
            )
        return updated
