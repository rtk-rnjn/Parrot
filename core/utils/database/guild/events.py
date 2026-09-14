from __future__ import annotations

from typing import Literal

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration

EVENT_NAME = Literal[
    "on_member_join",
    "on_member_leave",
    "on_member_ban",
    "on_member_unban",
    "on_message_delete",
    "on_message_edit",
    "on_channel_delete",
    "on_channel_create",
    "on_channel_update",
    "on_thread_create",
    "on_thread_delete",
    "on_thread_update",
    "on_server_update",
    "on_webhook_update",
    "on_role_create",
    "on_role_delete",
    "on_role_update",
    "on_member_join_voice",
    "on_member_leave_voice",
    "on_member_move_voice",
]


class _GuildEventsxMixin:
    """Guild command prefix operations."""

    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    async def is_event_enabled(self, guild_id: int, *, event_name: EVENT_NAME) -> bool:
        key = RedisKeys.GUILD_EVENT_ENABLED.format(guild_id=guild_id, event_name=event_name)
        enabled = await self.redis_client.get(key)
        if enabled is not None:
            return bool(int(enabled))

        guild_config = await self.guilds_collection.find_one(
            {"_id": guild_id, f"events.{event_name}.enabled": {"$exists": True}},
            {"_id": 0, f"events.{event_name}.enabled": 1},
        )

        if guild_config is not None:
            enabled = guild_config["events"][event_name]["enabled"]
            await self.redis_client.set(key, int(enabled))
            return bool(int(enabled))

        return False

    async def enable_event(self, guild_id: int, *, event_name: EVENT_NAME) -> None:
        key = RedisKeys.GUILD_EVENT_ENABLED.format(guild_id=guild_id, event_name=event_name)
        await self.redis_client.set(key, 1)
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"events.{event_name}.enabled": True}},
            upsert=True,
        )

    async def disable_event(self, guild_id: int, *, event_name: EVENT_NAME) -> None:
        key = RedisKeys.GUILD_EVENT_ENABLED.format(guild_id=guild_id, event_name=event_name)
        await self.redis_client.set(key, 0)
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"events.{event_name}.enabled": False}},
            upsert=True,
        )


    async def set_event_webhook(self, guild_id: int, *, event_name: EVENT_NAME, webhook_uri: str | None) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"events.{event_name}.webhook_uri": webhook_uri}},
            upsert=True,
        )
        key = RedisKeys.GUILD_EVENT_WEBHOOK_URI.format(guild_id=guild_id, event_name=event_name)
        if webhook_uri is not None:
            await self.redis_client.set(key, webhook_uri)
        else:
            await self.redis_client.delete(key)
