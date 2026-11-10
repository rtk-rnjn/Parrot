from __future__ import annotations

import re
from typing import Any

from bson import ObjectId

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin
from ..models import CustomCommand

_DB_KEY = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_DB_MAX_VALUE_LENGTH = 2000

MISSING: Any = sentinel("MISSING")


def _db_hash_key(guild_id: int) -> str:
    return RedisKeys.GUILD_CUSTOM_COMMAND_DB.format(guild_id=guild_id)


def _validate_db_key(key: str) -> str:
    if not _DB_KEY.match(key):
        msg = "database keys may only contain letters, numbers, '_' and '-' (max 64 characters)"
        raise ValueError(msg)
    return key


class _GuildCustomCommandsMixin(DatabaseMixin):
    """Persistence and cache operations for guild custom commands."""

    async def __cache_custom_command(self, guild_id: int, command: CustomCommand) -> None:
        await self.redis_client.set(
            RedisKeys.GUILD_CUSTOM_COMMAND_RESPONSE.format(guild_id=guild_id, command_name=command["name"]), command["response"]
        )
        if command.get("ignored_roles"):
            await self.redis_client.sadd(
                RedisKeys.GUILD_CUSTOM_COMMAND_IGNORED_ROLES.format(guild_id=guild_id, command_name=command["name"]), *command["ignored_roles"]
            )
        if command.get("ignored_channels"):
            await self.redis_client.sadd(
                RedisKeys.GUILD_CUSTOM_COMMAND_IGNORED_CHANNELS.format(guild_id=guild_id, command_name=command["name"]), *command["ignored_channels"]
            )
        await self.redis_client.set(
            RedisKeys.GUILD_CUSTOM_COMMAND_ENABLED.format(guild_id=guild_id, command_name=command["name"]), int(command["enabled"])
        )
        await self.redis_client.set(
            RedisKeys.GUILD_CUSTOM_COMMAND_REQUIRE_PREFIX.format(guild_id=guild_id, command_name=command["name"]),
            int(command.get("require_prefix", True)),
        )
        await self.redis_client.sadd(RedisKeys.GUILD_CUSTOM_COMMAND_NAMES.format(guild_id=guild_id), command["name"])

    async def __invalidate_custom_command_cache(self, guild_id: int, command_name: str) -> None:
        await self.redis_client.delete(RedisKeys.GUILD_CUSTOM_COMMAND_RESPONSE.format(guild_id=guild_id, command_name=command_name))
        await self.redis_client.delete(RedisKeys.GUILD_CUSTOM_COMMAND_IGNORED_ROLES.format(guild_id=guild_id, command_name=command_name))
        await self.redis_client.delete(RedisKeys.GUILD_CUSTOM_COMMAND_IGNORED_CHANNELS.format(guild_id=guild_id, command_name=command_name))
        await self.redis_client.delete(RedisKeys.GUILD_CUSTOM_COMMAND_ENABLED.format(guild_id=guild_id, command_name=command_name))
        await self.redis_client.srem(RedisKeys.GUILD_CUSTOM_COMMAND_NAMES.format(guild_id=guild_id), command_name)

    async def add_custom_command(
        self,
        *,
        guild_id: int,
        name: str,
        response: str,
        ignored_roles: list[int] | None = None,
        ignored_channels: list[int] | None = None,
        require_prefix: bool = True,
    ) -> bool:
        await self.custom_commands_collection.insert_one(
            {
                "_id": ObjectId(),
                "guild_id": guild_id,
                "name": name,
                "response": response,
                "ignored_roles": ignored_roles or [],
                "ignored_channels": ignored_channels or [],
                "enabled": True,
                "require_prefix": require_prefix,
            }
        )

        return True

    async def edit_custom_command(
        self,
        *,
        guild_id: int,
        name: str,
        response: str = MISSING,
        ignored_roles: list[int] = MISSING,
        ignored_channels: list[int] = MISSING,
        enabled: bool = MISSING,
        require_prefix: bool = MISSING,
    ) -> bool:
        payload = {}
        if response is not MISSING:
            payload["response"] = response
        if ignored_roles is not MISSING:
            payload["ignored_roles"] = ignored_roles
        if ignored_channels is not MISSING:
            payload["ignored_channels"] = ignored_channels
        if enabled is not MISSING:
            payload["enabled"] = enabled
        if require_prefix is not MISSING:
            payload["require_prefix"] = require_prefix

        result = await self.custom_commands_collection.update_one({"guild_id": guild_id, "name": name}, {"$set": payload})
        if result.matched_count == 0:
            return False

        await self.__invalidate_custom_command_cache(guild_id, name)
        return True

    async def delete_custom_command(self, *, guild_id: int, name: str) -> bool:
        result = await self.custom_commands_collection.delete_one({"guild_id": guild_id, "name": name})
        return result.deleted_count > 0

    async def rename_custom_command(self, *, guild_id: int, old_name: str, new_name: str) -> bool:
        result = await self.custom_commands_collection.update_one({"guild_id": guild_id, "name": old_name}, {"$set": {"name": new_name}})
        if result.matched_count == 0:
            return False

        await self.__invalidate_custom_command_cache(guild_id, old_name)
        return True

    async def get_custom_commands(self, guild_id: int, /) -> list[CustomCommand]:
        return await self.custom_commands_collection.find({"guild_id": guild_id}).to_list(length=None)

    async def get_custom_command(self, *, guild_id: int, name: str) -> CustomCommand | None:
        command = await self.custom_commands_collection.find_one({"guild_id": guild_id, "name": name})
        if command is None:
            return None
        await self.__cache_custom_command(guild_id, command)
        return command

    async def push_custom_command_log(self, *, guild_id: int, log_entry: str) -> None:
        await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$push": {"custom_commands_logs": {"$each": [log_entry], "$slice": -100}}},
            upsert=True,
        )

    async def get_custom_command_logs(self, *, guild_id: int) -> list[str]:
        guild = await self.guilds_collection.find_one({"_id": guild_id}, {"custom_commands_logs": 1})
        if guild is None:
            return []

        return guild.get("custom_commands_logs", [])

    async def clear_custom_command_logs(self, *, guild_id: int) -> None:
        await self.guilds_collection.update_one({"_id": guild_id}, {"$set": {"custom_commands_logs": []}})

    async def is_custom_command_enabled(self, *, guild_id: int, name: str) -> bool:
        cached = await self.redis_client.get(RedisKeys.GUILD_CUSTOM_COMMAND_ENABLED.format(guild_id=guild_id, command_name=name))
        if cached is not None:
            return bool(int(cached))

        command = await self.custom_commands_collection.find_one({"guild_id": guild_id, "name": name}, {"enabled": 1})
        if command is None:
            return False

        await self.redis_client.set(RedisKeys.GUILD_CUSTOM_COMMAND_ENABLED.format(guild_id=guild_id, command_name=name), int(command["enabled"]))
        return command["enabled"]

    async def does_custom_command_exist(self, *, guild_id: int, name: str) -> bool:
        cached = await self.redis_client.sismember(RedisKeys.GUILD_CUSTOM_COMMAND_NAMES.format(guild_id=guild_id), name)
        if cached:
            return True

        command = await self.custom_commands_collection.find_one({"guild_id": guild_id, "name": name}, {"_id": 1})
        if command is None:
            return False

        await self.redis_client.sadd(RedisKeys.GUILD_CUSTOM_COMMAND_NAMES.format(guild_id=guild_id), name)
        return True

    async def get_custom_command_response(self, *, guild_id: int, name: str) -> str | None:
        cached = await self.redis_client.get(RedisKeys.GUILD_CUSTOM_COMMAND_RESPONSE.format(guild_id=guild_id, command_name=name))
        if cached is not None:
            return cached.decode() if isinstance(cached, bytes) else cached

        command = await self.custom_commands_collection.find_one({"guild_id": guild_id, "name": name}, {"response": 1})
        if command is None:
            return None

        await self.redis_client.set(RedisKeys.GUILD_CUSTOM_COMMAND_RESPONSE.format(guild_id=guild_id, command_name=name), command["response"])
        return command["response"]

    async def get_custom_command_ignored_roles(self, *, guild_id: int, name: str) -> list[int]:
        cached = await self.redis_client.smembers(RedisKeys.GUILD_CUSTOM_COMMAND_IGNORED_ROLES.format(guild_id=guild_id, command_name=name))
        if cached:
            return [int(role_id) for role_id in cached]

        command = await self.custom_commands_collection.find_one({"guild_id": guild_id, "name": name}, {"ignored_roles": 1})
        if command is None:
            return []

        await self.redis_client.sadd(
            RedisKeys.GUILD_CUSTOM_COMMAND_IGNORED_ROLES.format(guild_id=guild_id, command_name=name), *command["ignored_roles"]
        )
        return command["ignored_roles"]

    async def get_custom_command_ignored_channels(self, *, guild_id: int, name: str) -> list[int]:
        cached = await self.redis_client.smembers(RedisKeys.GUILD_CUSTOM_COMMAND_IGNORED_CHANNELS.format(guild_id=guild_id, command_name=name))
        if cached:
            return [int(channel_id) for channel_id in cached]

        command = await self.custom_commands_collection.find_one({"guild_id": guild_id, "name": name}, {"ignored_channels": 1})
        if command is None:
            return []

        await self.redis_client.sadd(
            RedisKeys.GUILD_CUSTOM_COMMAND_IGNORED_CHANNELS.format(guild_id=guild_id, command_name=name), *command["ignored_channels"]
        )
        return command["ignored_channels"]

    async def does_custom_command_require_prefix(self, *, guild_id: int, name: str) -> bool:
        cached = await self.redis_client.get(RedisKeys.GUILD_CUSTOM_COMMAND_REQUIRE_PREFIX.format(guild_id=guild_id, command_name=name))
        if cached is not None:
            return bool(int(cached))

        command = await self.custom_commands_collection.find_one({"guild_id": guild_id, "name": name}, {"require_prefix": 1})
        if command is None:
            return True  # Default to requiring prefix if the command doesn't exist

        await self.redis_client.set(
            RedisKeys.GUILD_CUSTOM_COMMAND_REQUIRE_PREFIX.format(guild_id=guild_id, command_name=name), int(command.get("require_prefix", True))
        )
        return command.get("require_prefix", True)

    class CustomCommandInternalDatabase:
        def __init__(self, parent: _GuildCustomCommandsMixin):
            self.parent = parent
            self.redis_client = parent.redis_client
            self.collection = parent.guilds_collection

        async def set(self, *, guild_id: int, key: str, value: str) -> None:
            field = _validate_db_key(str(key))
            val = str(value)
            if len(val) > _DB_MAX_VALUE_LENGTH:
                msg = f"database values are limited to {_DB_MAX_VALUE_LENGTH} characters"
                raise ValueError(msg)

            await self.collection.update_one(
                {"_id": guild_id},
                {"$set": {f"custom_commands_db.{field}": val}},
                upsert=True,
            )
            await self.redis_client.hset(_db_hash_key(guild_id), field, val)

        async def get(self, *, guild_id: int, key: str, default: str | None = None) -> str | None:
            field = _validate_db_key(str(key))
            cached = await self.redis_client.hget(_db_hash_key(guild_id), field)
            if cached is not None:
                return cached.decode() if isinstance(cached, bytes) else cached

            guild = await self.collection.find_one({"_id": guild_id}, {f"custom_commands_db.{field}": 1})
            data = (guild or {}).get("custom_commands_db", {}).get(field)
            if data is None:
                return default

            await self.redis_client.hset(_db_hash_key(guild_id), field, data)
            return data

        async def delete(self, *, guild_id: int, key: str) -> None:
            field = _validate_db_key(str(key))
            await self.collection.update_one({"_id": guild_id}, {"$unset": {f"custom_commands_db.{field}": ""}})
            await self.redis_client.hdel(_db_hash_key(guild_id), field)

        async def exists(self, *, guild_id: int, key: str) -> bool:
            field = _validate_db_key(str(key))
            if await self.redis_client.hexists(_db_hash_key(guild_id), field):
                return True

            guild = await self.collection.find_one({"_id": guild_id}, {f"custom_commands_db.{field}": 1})
            data = (guild or {}).get("custom_commands_db", {}).get(field)
            if data is None:
                return False

            await self.redis_client.hset(_db_hash_key(guild_id), field, data)
            return True

    @property
    def cc_internal_database(self) -> CustomCommandInternalDatabase:
        return self.CustomCommandInternalDatabase(self)
