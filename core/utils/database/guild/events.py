from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from discord.utils import MISSING

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin

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
    "on_role_create",
    "on_role_delete",
    "on_role_update",
    "on_member_join_voice",
    "on_member_leave_voice",
    "on_member_move_voice",
]


class _GuildEventsMixin(DatabaseMixin):
    """Guild event enablement and webhook operations."""

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

    async def get_event_webhook_uri(self, guild_id: int, *, event_name: EVENT_NAME) -> str | None:
        key = RedisKeys.GUILD_EVENT_WEBHOOK_URI.format(guild_id=guild_id, event_name=event_name)
        cached = await self.redis_client.get(key)
        if cached is not None:
            return cached if isinstance(cached, str) else cached.decode()

        guild_config = await self.guilds_collection.find_one(
            {"_id": guild_id, f"events.{event_name}.webhook_uri": {"$exists": True, "$ne": None}},
            {"_id": 0, f"events.{event_name}.webhook_uri": 1},
        )
        if guild_config is None:
            return None

        webhook_uri = guild_config["events"][event_name]["webhook_uri"]
        if webhook_uri is None:
            return None
        await self.redis_client.set(key, webhook_uri)
        return webhook_uri

    async def edit_events(
        self,
        guild_id: int,
        *,
        event_names: Iterable[EVENT_NAME],
        enabled: bool = MISSING,
        webhook_uri: str | None = MISSING,
    ) -> bool:
        """Apply the same ``enabled`` / ``webhook_uri`` change to several events in one write."""
        names = list(event_names)
        fields = [(field, value) for field, value in (("enabled", enabled), ("webhook_uri", webhook_uri)) if value is not MISSING]
        if not names or not fields:
            return False

        updates = {f"events.{name}.{field}": value for name in names for field, value in fields}
        result = await self.guilds_collection.update_one({"_id": guild_id}, {"$set": updates}, upsert=True)

        async with self.redis_client.pipeline(transaction=False) as pipe:
            for name in names:
                if enabled is not MISSING:
                    pipe.set(RedisKeys.GUILD_EVENT_ENABLED.format(guild_id=guild_id, event_name=name), int(enabled))
                if webhook_uri is not MISSING:
                    key = RedisKeys.GUILD_EVENT_WEBHOOK_URI.format(guild_id=guild_id, event_name=name)
                    if webhook_uri is None:
                        pipe.delete(key)
                    else:
                        pipe.set(key, webhook_uri)
            await pipe.execute()

        return result.matched_count > 0 or result.upserted_id is not None

    async def edit_event(
        self,
        guild_id: int,
        *,
        event_name: EVENT_NAME,
        enabled: bool = MISSING,
        webhook_uri: str | None = MISSING,
    ) -> bool:
        updates = {
            f"events.{event_name}.{field}": value for field, value in (("enabled", enabled), ("webhook_uri", webhook_uri)) if value is not MISSING
        }
        if not updates:
            return False

        result = await self.guilds_collection.update_one({"_id": guild_id}, {"$set": updates}, upsert=True)
        if enabled is not MISSING:
            await self.redis_client.set(
                RedisKeys.GUILD_EVENT_ENABLED.format(guild_id=guild_id, event_name=event_name),
                int(enabled),
            )
        if webhook_uri is not MISSING:
            key = RedisKeys.GUILD_EVENT_WEBHOOK_URI.format(guild_id=guild_id, event_name=event_name)
            if webhook_uri is None:
                await self.redis_client.delete(key)
            else:
                await self.redis_client.set(key, webhook_uri)
        return result.matched_count > 0 or result.upserted_id is not None
