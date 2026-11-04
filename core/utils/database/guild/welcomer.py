from __future__ import annotations

from typing import Literal, get_args

from discord.utils import MISSING

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin
from ..models import WelcomeConfig

WelcomeStyle = Literal["text", "embed", "card"]
WELCOME_STYLES: tuple[str, ...] = get_args(WelcomeStyle)
DEFAULT_WELCOME_STYLE: WelcomeStyle = "card"


class _GuildWelcomerMixin(DatabaseMixin):
    async def __cache_welcome_config(self, *, guild_id: int, config: WelcomeConfig) -> None:
        values = {
            RedisKeys.GUILD_WELCOME_CONFIG_ENABLED: int(config.get("enabled", False)),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_MESSAGE: config.get("on_member_join_message"),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_CHANNEL_ID: config.get("on_member_join_channel_id"),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_MESSAGE: config.get("on_member_leave_message"),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_CHANNEL_ID: config.get("on_member_leave_channel_id"),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_ROLE_ID: config.get("on_member_join_role_id"),
        }
        for key, value in values.items():
            redis_key = key.format(guild_id=guild_id)
            if value is None:
                await self.redis_client.delete(redis_key)
            else:
                await self.redis_client.set(redis_key, value)

        # Appearance settings: "unset" is cached as an empty string (styles cache their default),
        # so a join event never has to fall through to MongoDB just to learn a value is missing.
        appearance = {
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_STYLE: self.__normalize_style(config.get("on_member_join_style")),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_STYLE: self.__normalize_style(config.get("on_member_leave_style")),
            RedisKeys.GUILD_WELCOME_CONFIG_ACCENT_COLOR: config.get("accent_color"),
            RedisKeys.GUILD_WELCOME_CONFIG_BANNER_URL: config.get("banner_url"),
        }
        for key, value in appearance.items():
            await self.redis_client.set(key.format(guild_id=guild_id), "" if value is None else value)

    async def __invalidate_welcome_config_cache(self, *, guild_id: int) -> None:
        await self.redis_client.delete(
            RedisKeys.GUILD_WELCOME_CONFIG_ENABLED.format(guild_id=guild_id),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_MESSAGE.format(guild_id=guild_id),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_CHANNEL_ID.format(guild_id=guild_id),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_MESSAGE.format(guild_id=guild_id),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_CHANNEL_ID.format(guild_id=guild_id),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_ROLE_ID.format(guild_id=guild_id),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_STYLE.format(guild_id=guild_id),
            RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_STYLE.format(guild_id=guild_id),
            RedisKeys.GUILD_WELCOME_CONFIG_ACCENT_COLOR.format(guild_id=guild_id),
            RedisKeys.GUILD_WELCOME_CONFIG_BANNER_URL.format(guild_id=guild_id),
        )

    async def edit_welcome_config(
        self,
        *,
        guild_id: int,
        enabled: bool = MISSING,
        on_member_join_message: str | None = MISSING,
        on_member_join_channel_id: int | None = MISSING,
        on_member_join_role_id: int | None = MISSING,
        on_member_join_style: WelcomeStyle = MISSING,
        on_member_leave_message: str | None = MISSING,
        on_member_leave_channel_id: int | None = MISSING,
        on_member_leave_style: WelcomeStyle = MISSING,
        accent_color: int | None = MISSING,
        banner_url: str | None = MISSING,
    ) -> bool:
        for style in (on_member_join_style, on_member_leave_style):
            if style is not MISSING and style not in WELCOME_STYLES:
                msg = f"style must be one of {WELCOME_STYLES}, got {style!r}"
                raise ValueError(msg)
        if accent_color not in (MISSING, None) and not 0 <= accent_color <= 0xFFFFFF:
            msg = "accent_color must be between 0x000000 and 0xFFFFFF"
            raise ValueError(msg)
        if banner_url not in (MISSING, None) and not banner_url.startswith("https://"):
            msg = "banner_url must be an https:// URL"
            raise ValueError(msg)

        updates = {}
        for field, value in (
            ("enabled", enabled),
            ("on_member_join_message", on_member_join_message),
            ("on_member_join_channel_id", on_member_join_channel_id),
            ("on_member_join_role_id", on_member_join_role_id),
            ("on_member_join_style", on_member_join_style),
            ("on_member_leave_message", on_member_leave_message),
            ("on_member_leave_channel_id", on_member_leave_channel_id),
            ("on_member_leave_style", on_member_leave_style),
            ("accent_color", accent_color),
            ("banner_url", banner_url),
        ):
            if value is not MISSING:
                updates[f"welcome_config.{field}"] = value

        if not updates:
            return False

        result = await self.guilds_collection.update_one({"_id": guild_id}, {"$set": updates})
        if result.matched_count == 0:
            return False

        await self.__invalidate_welcome_config_cache(guild_id=guild_id)
        return True

    async def delete_welcome_config(self, *, guild_id: int) -> bool:
        result = await self.guilds_collection.update_one(
            {"_id": guild_id, "welcome_config": {"$exists": True}},
            {"$set": {"welcome_config": None}},
        )
        await self.__invalidate_welcome_config_cache(guild_id=guild_id)
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
        await self.__cache_welcome_config(guild_id=guild_id, config=welcome_config)
        return welcome_config["enabled"]

    async def get_welcome_join_message(self, guild_id: int, /) -> str | None:
        key = RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_MESSAGE.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            return value if isinstance(value, str) else value.decode()

        return await self.__get_welcome_config_value(
            guild_id=guild_id,
            field="on_member_join_message",
            query_field="welcome_config.on_member_join_message",
        )

    async def get_welcome_join_channel_id(self, guild_id: int, /) -> int | None:
        key = RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_CHANNEL_ID.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            return int(value)

        return await self.__get_welcome_config_value(
            guild_id=guild_id,
            field="on_member_join_channel_id",
            query_field="welcome_config.on_member_join_channel_id",
        )

    async def get_welcome_leave_message(self, guild_id: int, /) -> str | None:
        key = RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_MESSAGE.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            return value if isinstance(value, str) else value.decode()

        return await self.__get_welcome_config_value(
            guild_id=guild_id,
            field="on_member_leave_message",
            query_field="welcome_config.on_member_leave_message",
        )

    async def get_welcome_leave_channel_id(self, guild_id: int, /) -> int | None:
        key = RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_CHANNEL_ID.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            return int(value)

        return await self.__get_welcome_config_value(
            guild_id=guild_id,
            field="on_member_leave_channel_id",
            query_field="welcome_config.on_member_leave_channel_id",
        )

    async def __get_welcome_config_value(self, *, guild_id: int, field: str, query_field: str):
        config = await self.guilds_collection.find_one({"_id": guild_id, query_field: {"$exists": True}}, {"welcome_config": 1})
        if config is None:
            return None

        welcome_config = config["welcome_config"]
        await self.__cache_welcome_config(guild_id=guild_id, config=welcome_config)
        return welcome_config.get(field)

    async def get_welcome_join_role_id(self, guild_id: int, /) -> int | None:
        key = RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_ROLE_ID.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            return int(value)

        return await self.__get_welcome_config_value(
            guild_id=guild_id,
            field="on_member_join_role_id",
            query_field="welcome_config.on_member_join_role_id",
        )

    async def set_welcome_join_role_id(self, guild_id: int, role_id: int | None, /) -> bool:
        return await self.edit_welcome_config(guild_id=guild_id, on_member_join_role_id=role_id)

    @staticmethod
    def __normalize_style(value: str | None) -> WelcomeStyle:
        return value if value in WELCOME_STYLES else DEFAULT_WELCOME_STYLE  # type: ignore[return-value]

    async def __load_welcome_config(self, guild_id: int) -> WelcomeConfig | None:
        """Fetch the whole welcome config (even when it's partial), cache it, and return it."""
        doc = await self.guilds_collection.find_one(
            {"_id": guild_id, "welcome_config": {"$type": "object"}},
            {"welcome_config": 1},
        )
        if doc is None:
            return None

        welcome_config = doc["welcome_config"]
        await self.__cache_welcome_config(guild_id=guild_id, config=welcome_config)
        return welcome_config

    async def get_welcome_join_style(self, guild_id: int, /) -> WelcomeStyle:
        key = RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_STYLE.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            return self.__normalize_style(value if isinstance(value, str) else value.decode())

        config = await self.__load_welcome_config(guild_id)
        return self.__normalize_style(config.get("on_member_join_style") if config else None)

    async def get_welcome_leave_style(self, guild_id: int, /) -> WelcomeStyle:
        key = RedisKeys.GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_STYLE.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            return self.__normalize_style(value if isinstance(value, str) else value.decode())

        config = await self.__load_welcome_config(guild_id)
        return self.__normalize_style(config.get("on_member_leave_style") if config else None)

    async def get_welcome_accent_color(self, guild_id: int, /) -> int | None:
        key = RedisKeys.GUILD_WELCOME_CONFIG_ACCENT_COLOR.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            raw = value if isinstance(value, str) else value.decode()
            return int(raw) if raw else None  # "" means "not set"

        config = await self.__load_welcome_config(guild_id)
        return config.get("accent_color") if config else None

    async def get_welcome_banner_url(self, guild_id: int, /) -> str | None:
        key = RedisKeys.GUILD_WELCOME_CONFIG_BANNER_URL.format(guild_id=guild_id)
        value = await self.redis_client.get(key)
        if value is not None:
            raw = value if isinstance(value, str) else value.decode()
            return raw or None  # "" means "not set"

        config = await self.__load_welcome_config(guild_id)
        return config.get("banner_url") if config else None
