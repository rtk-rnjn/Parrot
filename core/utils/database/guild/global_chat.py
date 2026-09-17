from __future__ import annotations

from discord.utils import MISSING
from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin
from ..models import GuildConfiguration


class _GuildGlobalChatMixin(DatabaseMixin):
    """Guild global-chat configuration and channel operations."""

    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def is_global_chat_enabled(self, guild_id: int) -> bool:
        """Check if global chat is enabled for a guild."""
        key = RedisKeys.GUILD_GLOBAL_CHAT_CONFIG_ENABLED.format(guild_id=guild_id)
        enabled = await self.redis_client.get(key)
        if enabled is not None:
            return bool(int(enabled))

        guild_config = await self.guilds_collection.find_one({"_id": guild_id})
        if guild_config is None:
            return False

        enabled = guild_config.get("global_chat_config", {}).get("enabled", False)
        await self.redis_client.set(key, int(enabled))
        return enabled

    async def edit_global_chat_config(
        self,
        *,
        guild_id: int,
        enabled: bool = MISSING,
        channel_id: int | None = MISSING,
        webhook_uri: str | None = MISSING,
    ) -> bool:
        updates = {
            f"global_chat_config.{field}": value
            for field, value in (("enabled", enabled), ("channel_id", channel_id), ("webhook_uri", webhook_uri))
            if value is not MISSING
        }
        if not updates:
            return False

        result = await self.guilds_collection.update_one({"_id": guild_id}, {"$set": updates}, upsert=True)
        for field, value in (("enabled", enabled), ("channel_id", channel_id), ("webhook_uri", webhook_uri)):
            if value is MISSING:
                continue
            key = getattr(
                RedisKeys,
                f"GUILD_GLOBAL_CHAT_CONFIG_{field.upper()}" if field != "webhook_uri" else "GUILD_GLOBAL_CHAT_CONFIG_WEBHOOK_URI",
            )
            redis_key = key.format(guild_id=guild_id)
            if value is None:
                await self.redis_client.delete(redis_key)
            else:
                await self.redis_client.set(redis_key, int(value) if isinstance(value, bool) else value)
        return result.matched_count > 0 or result.upserted_id is not None

    async def get_global_chat_channel_id(self, guild_id: int) -> int | None:
        """Get the global chat channel ID for a guild."""
        key = RedisKeys.GUILD_GLOBAL_CHAT_CONFIG_CHANNEL_ID.format(guild_id=guild_id)
        channel_id = await self.redis_client.get(key)
        if channel_id is not None:
            return int(channel_id)

        guild_config = await self.guilds_collection.find_one({"_id": guild_id, "global_chat_config.channel_id": {"$exists": True}})
        if guild_config is None:
            return None

        channel_id = guild_config["global_chat_config"]["channel_id"]
        if channel_id is not None:
            await self.redis_client.set(key, channel_id)
        return channel_id

    async def get_global_chat_webhook_uri(self, guild_id: int) -> str | None:
        """Get the global chat webhook URI for a guild."""
        key = RedisKeys.GUILD_GLOBAL_CHAT_CONFIG_WEBHOOK_URI.format(guild_id=guild_id)
        webhook_uri = await self.redis_client.get(key)
        if webhook_uri is not None and isinstance(webhook_uri, str):
            return webhook_uri

        guild_config = await self.guilds_collection.find_one({"_id": guild_id, "global_chat_config.webhook_uri": {"$exists": True}})
        if guild_config is None:
            return None

        webhook_uri = guild_config["global_chat_config"]["webhook_uri"]
        if webhook_uri is not None:
            await self.redis_client.set(key, webhook_uri)
        return webhook_uri

    async def fetch_active_global_chat_webhooks(self):
        """Get all global chat webhook URIs."""
        filters = {
            "global_chat_config.webhook_uri": {"$exists": True, "$ne": None},
            "global_chat_config.enabled": True,
        }

        projection = {"_id": 1, "global_chat_config.webhook_uri": 1}
        async for guild in self.guilds_collection.find(filters, projection):
            guild_id = guild["_id"]
            webhook_uri = guild["global_chat_config"]["webhook_uri"]
            yield guild_id, webhook_uri
