from __future__ import annotations

import json
import re

from discord.utils import MISSING
from pymongo.errors import DuplicateKeyError

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin
from ..models import CustomCommand

_LOADED_FIELD = ":loaded"
_CACHE_TTL_SECONDS = 6 * 60 * 60
_DB_KEY = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_DB_MAX_VALUE_LENGTH = 2000


def _db_hash_key(guild_id: int) -> str:
    return RedisKeys.GUILD_CUSTOM_COMMAND_DB.format(guild_id=guild_id)


def _validate_db_key(key: str) -> str:
    if not _DB_KEY.match(key):
        msg = "database keys may only contain letters, numbers, '_' and '-' (max 64 characters)"
        raise ValueError(msg)
    return key


class _GuildCustomCommandsMixin(DatabaseMixin):
    """Persistence and cache operations for guild custom commands."""

    def __custom_commands_key(self, guild_id: int) -> str:
        return RedisKeys.GUILD_CUSTOM_COMMANDS.format(guild_id=guild_id)

    async def __invalidate_custom_commands_cache(self, guild_id: int) -> None:
        await self.redis_client.delete(self.__custom_commands_key(guild_id))

    async def get_custom_command_cached(self, *, guild_id: int, name: str) -> CustomCommand | None:
        key = self.__custom_commands_key(guild_id)
        raw, loaded = await self.redis_client.hmget(key, name, _LOADED_FIELD)
        if raw is not None:
            return json.loads(raw)
        if loaded is not None:
            return None

        custom_commands = await self.get_custom_commands(guild_id)
        mapping = {command["name"]: json.dumps(command) for command in custom_commands}
        mapping[_LOADED_FIELD] = "1"
        await self.redis_client.hset(key, mapping=mapping)
        await self.redis_client.expire(key, _CACHE_TTL_SECONDS)

        return next((command for command in custom_commands if command["name"] == name), None)

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
        try:
            await self.guilds_collection.update_one(
                {"_id": guild_id, "custom_commands.name": {"$ne": name}},
                {
                    "$push": {
                        "custom_commands": {
                            "name": name,
                            "response": response,
                            "ignored_roles": ignored_roles or [],
                            "ignored_channels": ignored_channels or [],
                            "enabled": True,
                            "require_prefix": require_prefix,
                        }
                    }
                },
                upsert=True,
            )
        except DuplicateKeyError:
            return False

        await self.__invalidate_custom_commands_cache(guild_id)
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
        fields = {
            "response": response,
            "ignored_roles": ignored_roles,
            "ignored_channels": ignored_channels,
            "enabled": enabled,
            "require_prefix": require_prefix,
        }
        payload = {f"custom_commands.$.{field}": value for field, value in fields.items() if value is not MISSING}
        if not payload:
            return False

        result = await self.guilds_collection.update_one({"_id": guild_id, "custom_commands.name": name}, {"$set": payload})
        if result.matched_count == 0:
            return False

        await self.__invalidate_custom_commands_cache(guild_id)
        return True

    async def delete_custom_command(self, *, guild_id: int, name: str) -> bool:
        result = await self.guilds_collection.update_one(
            {"_id": guild_id, "custom_commands.name": name},
            {"$pull": {"custom_commands": {"name": name}}},
        )
        if result.matched_count == 0:
            return False

        await self.__invalidate_custom_commands_cache(guild_id)
        return True

    async def rename_custom_command(self, *, guild_id: int, old_name: str, new_name: str) -> bool:
        result = await self.guilds_collection.update_one(
            {
                "_id": guild_id,
                "$and": [
                    {"custom_commands.name": old_name},
                    {"custom_commands.name": {"$ne": new_name}},
                ],
            },
            {"$set": {"custom_commands.$[command].name": new_name}},
            array_filters=[{"command.name": old_name}],
        )
        if result.matched_count == 0:
            return False

        await self.__invalidate_custom_commands_cache(guild_id)
        return True

    async def get_custom_commands(self, guild_id: int, /) -> list[CustomCommand]:
        guild = await self.guilds_collection.find_one({"_id": guild_id}, {"custom_commands": 1})
        if guild is None:
            return []

        return guild.get("custom_commands", [])

    async def get_custom_command(self, *, guild_id: int, name: str) -> CustomCommand | None:
        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "custom_commands.name": name},
            {"custom_commands": {"$elemMatch": {"name": name}}},
        )
        if guild is None:
            return None

        results = guild.get("custom_commands", [])
        return results[0] if results else None

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
