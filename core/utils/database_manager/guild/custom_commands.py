from __future__ import annotations

from discord.utils import MISSING
from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import CustomCommand, GuildConfiguration

_CACHE_TTL = 3600


class _GuildCustomCommandsMixin:
    """Persistence and cache operations for guild custom commands."""

    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    def _custom_command_names_key(self, guild_id: int) -> str:
        return RedisKeys.GUILD_CUSTOM_COMMAND_NAMES.format(guild_id=guild_id)

    def _custom_command_response_key(self, guild_id: int, name: str) -> str:
        return RedisKeys.GUILD_CUSTOM_COMMAND_RESPONSE.format(guild_id=guild_id, command_name=name)

    def _custom_command_ignored_roles_key(self, guild_id: int, name: str) -> str:
        return RedisKeys.GUILD_CUSTOM_COMMAND_IGNORED_ROLES.format(guild_id=guild_id, command_name=name)

    def _custom_command_ignored_channels_key(self, guild_id: int, name: str) -> str:
        return RedisKeys.GUILD_CUSTOM_COMMAND_IGNORED_CHANNELS.format(guild_id=guild_id, command_name=name)

    def _custom_command_enabled_key(self, guild_id: int, name: str) -> str:
        return RedisKeys.GUILD_CUSTOM_COMMAND_ENABLED.format(guild_id=guild_id, command_name=name)

    async def _cache_custom_command(  # noqa: PLR0913
        self,
        *,
        guild_id: int,
        name: str,
        response: str,
        ignored_roles: list[int] | None = None,
        ignored_channels: list[int] | None = None,
        enabled: bool = True,
    ) -> None:
        names_key = self._custom_command_names_key(guild_id)

        await self.redis_client.sadd(names_key, name)
        await self.redis_client.expire(names_key, _CACHE_TTL)

        await self.redis_client.set(self._custom_command_response_key(guild_id, name), response, ex=_CACHE_TTL)

        if ignored_roles:
            await self.redis_client.sadd(self._custom_command_ignored_roles_key(guild_id, name), *ignored_roles)
            await self.redis_client.expire(self._custom_command_ignored_roles_key(guild_id, name), _CACHE_TTL)

        if ignored_channels:
            await self.redis_client.sadd(self._custom_command_ignored_channels_key(guild_id, name), *ignored_channels or [])
            await self.redis_client.expire(self._custom_command_ignored_channels_key(guild_id, name), _CACHE_TTL)

        await self.redis_client.set(self._custom_command_enabled_key(guild_id, name), int(enabled), ex=_CACHE_TTL)

    async def _invalidate_custom_command_cache(self, *, guild_id: int, name: str) -> None:
        names_key = self._custom_command_names_key(guild_id)

        await self.redis_client.srem(names_key, name)
        await self.redis_client.delete(self._custom_command_response_key(guild_id, name))
        await self.redis_client.delete(self._custom_command_ignored_roles_key(guild_id, name))
        await self.redis_client.delete(self._custom_command_ignored_channels_key(guild_id, name))
        await self.redis_client.delete(self._custom_command_enabled_key(guild_id, name))

    async def get_custom_command_response(
        self,
        *,
        guild_id: int,
        name: str,
    ) -> str | None:
        """Return one custom command response, or ``None`` when it does not exist."""
        response_key = self._custom_command_response_key(guild_id, name)
        cached_response = await self.redis_client.get(response_key)

        if isinstance(cached_response, str):
            return cached_response

        guild = await self.guilds_collection.find_one(
            {
                "_id": guild_id,
                "custom_commands.name": name,
            },
            {
                "custom_commands": {
                    "$elemMatch": {"name": name},
                },
            },
        )

        if guild is None:
            return None

        results = guild.get("custom_commands", [])
        if not results:
            return None

        command = results[0]

        response = command["response"]
        await self._cache_custom_command(guild_id=guild_id, **command)

        return response

    async def add_custom_command(
        self,
        *,
        guild_id: int,
        name: str,
        response: str,
        ignored_roles: list[int] | None = None,
        ignored_channels: list[int] | None = None,
    ) -> bool:
        """Add a command without overwriting an existing command."""
        result = await self.guilds_collection.update_one(
            {"_id": guild_id, "custom_commands.name": {"$ne": name}},
            {
                "$push": {
                    "custom_commands": {
                        "name": name,
                        "response": response,
                        "ignored_roles": ignored_roles or [],
                        "ignored_channels": ignored_channels or [],
                        "enabled": True,
                    },
                },
            },
            upsert=True,
        )

        if result.matched_count == 0 and result.upserted_id is None:
            return False

        await self._cache_custom_command(
            guild_id=guild_id,
            name=name,
            response=response,
            ignored_roles=ignored_roles,
            ignored_channels=ignored_channels,
            enabled=True,
        )
        return True

    async def edit_custom_command(  # noqa: PLR0913
        self,
        *,
        guild_id: int,
        name: str,
        response: str = MISSING,
        ignored_roles: list[int] = MISSING,
        ignored_channels: list[int] = MISSING,
        enabled: bool = MISSING,
    ) -> bool:
        """Update an existing command response."""
        payload = {}
        if response is not MISSING:
            payload["custom_commands.$.response"] = response
        if ignored_roles is not MISSING:
            payload["custom_commands.$.ignored_roles"] = ignored_roles
        if ignored_channels is not MISSING:
            payload["custom_commands.$.ignored_channels"] = ignored_channels
        if enabled is not MISSING:
            payload["custom_commands.$.enabled"] = enabled

        result = await self.guilds_collection.update_one(
            {"_id": guild_id, "custom_commands.name": name},
            {
                "$set": payload,
            },
        )

        if result.matched_count == 0:
            return False

        await self._invalidate_custom_command_cache(guild_id=guild_id, name=name)
        return True

    async def delete_custom_command(
        self,
        *,
        guild_id: int,
        name: str,
    ) -> bool:
        """Delete an existing command."""
        result = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$pull": {"custom_commands": {"name": name}}},
        )
        if result.matched_count == 0:
            return False
        await self._invalidate_custom_command_cache(guild_id=guild_id, name=name)
        return True

    async def get_custom_commands(self, guild_id: int, /) -> list[CustomCommand]:
        """Return all custom commands for a guild."""
        guild = await self.guilds_collection.find_one(
            {"_id": guild_id},
            {"custom_commands": 1},
        )
        if guild is None:
            return []

        return guild.get("custom_commands", [])

    async def rename_custom_command(
        self,
        *,
        guild_id: int,
        old_name: str,
        new_name: str,
    ) -> bool:
        """Rename an existing command."""
        result = await self.guilds_collection.update_one(
            {"_id": guild_id, "custom_commands.name": old_name},
            {
                "$set": {
                    "custom_commands.$.name": new_name,
                },
            },
        )

        if result.matched_count == 0:
            return False

        await self._invalidate_custom_command_cache(guild_id=guild_id, name=old_name)
        return True

    async def disable_custom_command(
        self,
        *,
        guild_id: int,
        name: str,
    ) -> bool:
        """Disable an existing command."""
        return await self.edit_custom_command(guild_id=guild_id, name=name, enabled=False)

    async def enable_custom_command(
        self,
        *,
        guild_id: int,
        name: str,
    ) -> bool:
        """Enable an existing command."""
        return await self.edit_custom_command(guild_id=guild_id, name=name, enabled=True)

    async def get_custom_command(self, *, guild_id: int, name: str) -> CustomCommand | None:
        """Return a custom command object for a guild."""
        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "custom_commands.name": name},
            {"custom_commands": {"$elemMatch": {"name": name}}},
        )
        if guild is None:
            return None

        results = guild.get("custom_commands", [])
        if not results:
            return None

        command_data = results[0]
        await self._cache_custom_command(guild_id=guild_id, **command_data)

        return command_data

    async def push_custom_command_log(self, *, guild_id: int, log_entry: str) -> None:
        """Push a log entry for a custom command."""
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {
                "$push": {
                    "custom_commands_logs": {
                        "$each": [log_entry],
                        "$slice": -100,
                    },
                },
            },
            upsert=True,
        )

    async def get_custom_command_logs(self, *, guild_id: int) -> list[str]:
        """Return all custom command logs for a guild."""
        guild = await self.guilds_collection.find_one(
            {"_id": guild_id},
            {"custom_commands_logs": 1},
        )
        if guild is None:
            return []

        return guild.get("custom_commands_logs", [])

    async def clear_custom_command_logs(self, *, guild_id: int) -> None:
        """Clear all custom command logs for a guild."""
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {"custom_commands_logs": []}},
        )

    async def set_custom_command_db(self, *, guild_id: int, key: str, value: str) -> None:
        """Set a key-value pair in the custom command database for a guild."""
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$set": {f"custom_commands_db.{key}": value}},
            upsert=True,
        )

        key = RedisKeys.GUILD_CUSTOM_COMMAND_DB.format(guild_id=guild_id)
        await self.redis_client.hset(key, key, value)

    async def get_custom_command_db(self, *, guild_id: int, key: str) -> str | None:
        """Get a value from the custom command database for a guild."""
        key = RedisKeys.GUILD_CUSTOM_COMMAND_DB.format(guild_id=guild_id)
        cached_value = await self.redis_client.hget(key, key)
        if cached_value is not None and isinstance(cached_value, str):
            return cached_value

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id},
            {f"custom_commands_db.{key}": 1},
        )
        if guild is None:
            return None

        data = guild.get("custom_commands_db", {}).get(key)
        if data is not None:
            await self.redis_client.hset(key, key, data)

        return data
