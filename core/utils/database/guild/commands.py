from __future__ import annotations

from discord.utils import MISSING
from pymongo import UpdateOne

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin
from ..models import CommandConfig


class _GuildCommandConfigMixin(DatabaseMixin):
    async def __cache_command_config(self, *, guild_id: int, config: CommandConfig | None) -> None:
        """Cache a command config for a guild."""
        if config is None:
            return

        if config["command_path"] is None:
            return

        await self.redis_client.set(
            RedisKeys.COMMAND_CONFIG_ENABLED.format(guild_id=guild_id, command_path=config["command_path"]),
            int(config["enabled"]),
        )

        if config["ignored_roles"]:
            await self.redis_client.sadd(
                RedisKeys.COMMAND_CONFIG_IGNORED_ROLES.format(guild_id=guild_id, command_path=config["command_path"]),
                *config["ignored_roles"],
            )

        if config["allowed_roles"]:
            await self.redis_client.sadd(
                RedisKeys.COMMAND_CONFIG_ALLOWED_ROLES.format(guild_id=guild_id, command_path=config["command_path"]),
                *config["allowed_roles"],
            )

        if config["ignored_channels"]:
            await self.redis_client.sadd(
                RedisKeys.COMMAND_CONFIG_IGNORED_CHANNELS.format(guild_id=guild_id, command_path=config["command_path"]),
                *config["ignored_channels"],
            )

        if config["allowed_channels"]:
            await self.redis_client.sadd(
                RedisKeys.COMMAND_CONFIG_ALLOWED_CHANNELS.format(guild_id=guild_id, command_path=config["command_path"]),
                *config["allowed_channels"],
            )

    async def __invalidate_command_config_cache(self, *, guild_id: int, command_path: str) -> None:
        """Invalidate the cache for a command config for a guild."""
        await self.redis_client.delete(
            RedisKeys.COMMAND_CONFIG_ENABLED.format(guild_id=guild_id, command_path=command_path),
            RedisKeys.COMMAND_CONFIG_IGNORED_ROLES.format(guild_id=guild_id, command_path=command_path),
            RedisKeys.COMMAND_CONFIG_ALLOWED_ROLES.format(guild_id=guild_id, command_path=command_path),
            RedisKeys.COMMAND_CONFIG_IGNORED_CHANNELS.format(guild_id=guild_id, command_path=command_path),
            RedisKeys.COMMAND_CONFIG_ALLOWED_CHANNELS.format(guild_id=guild_id, command_path=command_path),
        )

    async def is_command_registered(self, *, guild_id: int, command_path: str) -> bool:
        key = RedisKeys.COMMAND_CONFIG_ENABLED.format(guild_id=guild_id, command_path=command_path)
        if await self.redis_client.exists(key):
            return True

        exists = await self.commands_config_collection.count_documents({"guild_id": guild_id, "command_path": command_path}, limit=1) > 0
        if exists:
            config = await self.commands_config_collection.find_one({"guild_id": guild_id, "command_path": command_path})
            await self.__cache_command_config(
                guild_id=guild_id,
                config=config,
            )
            return True

        return False

    async def is_command_enabled(self, *, guild_id: int, command_path: str) -> bool:
        """Commands without a config row are enabled by default."""
        key = RedisKeys.COMMAND_CONFIG_ENABLED.format(guild_id=guild_id, command_path=command_path)
        cached = await self.redis_client.get(key)
        if cached is not None:
            return bool(int(cached))

        config = await self.commands_config_collection.find_one({"guild_id": guild_id, "command_path": command_path})
        if config is None:
            return True

        await self.__cache_command_config(guild_id=guild_id, config=config)
        return bool(config["enabled"])

    async def register_command_config(self, *, guild_id: int, command_path: str) -> None:
        """Register a command config for a guild."""
        if await self.is_command_registered(guild_id=guild_id, command_path=command_path):
            return

        payload: CommandConfig = {
            "guild_id": guild_id,
            "command_path": command_path,
            "enabled": True,
            "ignored_roles": [],
            "allowed_roles": [],
            "ignored_channels": [],
            "allowed_channels": [],
        }
        await self.commands_config_collection.insert_one(payload)
        await self.__cache_command_config(guild_id=guild_id, config=payload)

    async def edit_command_config(
        self,
        *,
        guild_id: int,
        command_path: str,
        enabled: bool | None = MISSING,
        ignored_roles: list[int] | None = MISSING,
        allowed_roles: list[int] | None = MISSING,
        ignored_channels: list[int] | None = MISSING,
        allowed_channels: list[int] | None = MISSING,
    ):
        """Edit a command config for a guild."""
        update_fields = {}
        if enabled is not MISSING:
            update_fields["enabled"] = enabled
        if ignored_roles is not MISSING:
            update_fields["ignored_roles"] = ignored_roles
        if allowed_roles is not MISSING:
            update_fields["allowed_roles"] = allowed_roles
        if ignored_channels is not MISSING:
            update_fields["ignored_channels"] = ignored_channels
        if allowed_channels is not MISSING:
            update_fields["allowed_channels"] = allowed_channels

        if not update_fields:
            return

        await self.commands_config_collection.update_one(
            {"guild_id": guild_id, "command_path": command_path},
            {"$set": update_fields},
            upsert=True,
        )
        await self.__invalidate_command_config_cache(guild_id=guild_id, command_path=command_path)
        return

    async def edit_commands_config(
        self,
        *,
        guild_id: int,
        command_paths: list[str],
        enabled: bool | None = MISSING,
        ignored_roles: list[int] | None = MISSING,
        allowed_roles: list[int] | None = MISSING,
        ignored_channels: list[int] | None = MISSING,
        allowed_channels: list[int] | None = MISSING,
    ) -> None:
        """Edit many command configs at once. Fields left as MISSING are not touched."""
        if not command_paths:
            return

        fields = {
            name: value
            for name, value in (
                ("enabled", enabled),
                ("ignored_roles", ignored_roles),
                ("allowed_roles", allowed_roles),
                ("ignored_channels", ignored_channels),
                ("allowed_channels", allowed_channels),
            )
            if value is not MISSING
        }
        if not fields:
            return

        defaults = {"enabled": True, "ignored_roles": [], "allowed_roles": [], "ignored_channels": [], "allowed_channels": []}
        update: dict = {"$set": fields}
        on_insert = {key: value for key, value in defaults.items() if key not in fields}
        if on_insert:
            update["$setOnInsert"] = on_insert

        await self.commands_config_collection.bulk_write(
            [UpdateOne({"guild_id": guild_id, "command_path": path}, update, upsert=True) for path in command_paths]
        )

        templates = (
            RedisKeys.COMMAND_CONFIG_ENABLED,
            RedisKeys.COMMAND_CONFIG_IGNORED_ROLES,
            RedisKeys.COMMAND_CONFIG_ALLOWED_ROLES,
            RedisKeys.COMMAND_CONFIG_IGNORED_CHANNELS,
            RedisKeys.COMMAND_CONFIG_ALLOWED_CHANNELS,
        )
        await self.redis_client.delete(*(template.format(guild_id=guild_id, command_path=path) for path in command_paths for template in templates))

    async def set_commands_enabled(self, *, guild_id: int, command_paths: list[str], enabled: bool) -> None:
        await self.edit_commands_config(guild_id=guild_id, command_paths=command_paths, enabled=enabled)

    async def get_guild_command_configs(self, *, guild_id: int) -> list[CommandConfig]:
        """All command configs stored for a guild."""
        return await self.commands_config_collection.find({"guild_id": guild_id}).to_list(length=None)

    async def get_command_config_ignored_roles(self, *, guild_id: int, command_path: str) -> list[int]:
        """Get the ignored roles for a command config for a guild."""
        key = RedisKeys.COMMAND_CONFIG_IGNORED_ROLES.format(guild_id=guild_id, command_path=command_path)
        if await self.redis_client.exists(key):
            return [int(role_id) for role_id in await self.redis_client.smembers(key)]

        config = await self.commands_config_collection.find_one({"guild_id": guild_id, "command_path": command_path})
        if config is None:
            return []

        await self.__cache_command_config(guild_id=guild_id, config=config)
        return config.get("ignored_roles", [])

    async def get_command_config_allowed_roles(self, *, guild_id: int, command_path: str) -> list[int]:
        """Get the allowed roles for a command config for a guild."""
        key = RedisKeys.COMMAND_CONFIG_ALLOWED_ROLES.format(guild_id=guild_id, command_path=command_path)
        if await self.redis_client.exists(key):
            return [int(role_id) for role_id in await self.redis_client.smembers(key)]

        config = await self.commands_config_collection.find_one({"guild_id": guild_id, "command_path": command_path})
        if config is None:
            return []

        await self.__cache_command_config(guild_id=guild_id, config=config)
        return config.get("allowed_roles", [])

    async def get_command_config_ignored_channels(self, *, guild_id: int, command_path: str) -> list[int]:
        """Get the ignored channels for a command config for a guild."""
        key = RedisKeys.COMMAND_CONFIG_IGNORED_CHANNELS.format(guild_id=guild_id, command_path=command_path)
        if await self.redis_client.exists(key):
            return [int(channel_id) for channel_id in await self.redis_client.smembers(key)]

        config = await self.commands_config_collection.find_one({"guild_id": guild_id, "command_path": command_path})
        if config is None:
            return []

        await self.__cache_command_config(guild_id=guild_id, config=config)
        return config.get("ignored_channels", [])

    async def get_command_config_allowed_channels(self, *, guild_id: int, command_path: str) -> list[int]:
        """Get the allowed channels for a command config for a guild."""
        key = RedisKeys.COMMAND_CONFIG_ALLOWED_CHANNELS.format(guild_id=guild_id, command_path=command_path)
        if await self.redis_client.exists(key):
            return [int(channel_id) for channel_id in await self.redis_client.smembers(key)]

        config = await self.commands_config_collection.find_one({"guild_id": guild_id, "command_path": command_path})
        if config is None:
            return []

        await self.__cache_command_config(guild_id=guild_id, config=config)
        return config.get("allowed_channels", [])
