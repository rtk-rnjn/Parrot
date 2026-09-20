from __future__ import annotations

from discord.utils import MISSING

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin


class _GuildTicketMixin(DatabaseMixin):
    async def __invalidate_ticket_config_cache(self, guild_id: int) -> None:
        await self.redis_client.delete(
            RedisKeys.GUILD_TICKET_CONFIG_CHANNEL_ID.format(guild_id=guild_id),
            RedisKeys.GUILD_TICKET_CONFIG_ENABLED.format(guild_id=guild_id),
            RedisKeys.GUILD_TICKET_CONFIG_USE_THREAD.format(guild_id=guild_id),
            RedisKeys.GUILD_TICKET_CONFIG_CATEGORY_ID.format(guild_id=guild_id),
            RedisKeys.GUILD_TICKET_CONFIG_BOT_MESSAGE_ID.format(guild_id=guild_id),
            RedisKeys.GUILD_TICKET_CONFIG_BOT_CHANNEL_ID.format(guild_id=guild_id),
        )

    async def is_ticket_config_enabled(self, guild_id: int, /) -> bool:
        key = RedisKeys.GUILD_TICKET_CONFIG_ENABLED.format(guild_id=guild_id)
        cached = await self.redis_client.get(key)
        if cached is not None:
            return bool(int(cached))

        guild = await self.guilds_collection.find_one({"_id": guild_id, "ticket_config.enabled": {"$exists": True}}, {"ticket_config.enabled": 1})
        if guild is None:
            return False
        enabled = bool(guild["ticket_config"]["enabled"])
        await self.redis_client.set(key, int(enabled))
        return enabled

    async def is_ticket_config_use_thread(self, guild_id: int, /) -> bool:
        key = RedisKeys.GUILD_TICKET_CONFIG_USE_THREAD.format(guild_id=guild_id)
        cached = await self.redis_client.get(key)
        if cached is not None:
            return bool(int(cached))

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "ticket_config.use_thread": {"$exists": True}},
            {"ticket_config.use_thread": 1},
        )
        if guild is None:
            return False
        use_thread = bool(guild["ticket_config"]["use_thread"])
        await self.redis_client.set(key, int(use_thread))
        return use_thread

    async def get_ticket_config_channel_id(self, guild_id: int, /) -> int | None:
        key = RedisKeys.GUILD_TICKET_CONFIG_CHANNEL_ID.format(guild_id=guild_id)
        cached = await self.redis_client.get(key)
        if cached is not None:
            return int(cached)

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "ticket_config.channel_id": {"$exists": True}},
            {"ticket_config.channel_id": 1},
        )
        if guild is None:
            return None
        channel_id = guild["ticket_config"]["channel_id"]
        if channel_id is not None:
            await self.redis_client.set(key, channel_id)
        return channel_id

    async def get_ticket_config_category_id(self, guild_id: int, /) -> int | None:
        key = RedisKeys.GUILD_TICKET_CONFIG_CATEGORY_ID.format(guild_id=guild_id)
        cached = await self.redis_client.get(key)
        if cached is not None:
            return int(cached)

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "ticket_config.category_id": {"$exists": True}},
            {"ticket_config.category_id": 1},
        )
        if guild is None:
            return None
        category_id = guild["ticket_config"]["category_id"]
        if category_id is not None:
            await self.redis_client.set(key, category_id)
        return category_id

    async def get_ticket_config_bot_message_id(self, guild_id: int, /) -> int | None:
        key = RedisKeys.GUILD_TICKET_CONFIG_BOT_MESSAGE_ID.format(guild_id=guild_id)
        cached = await self.redis_client.get(key)
        if cached is not None:
            return int(cached)

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "ticket_config.bot_message_id": {"$exists": True}},
            {"ticket_config.bot_message_id": 1},
        )
        if guild is None:
            return None
        bot_message_id = guild["ticket_config"]["bot_message_id"]
        if bot_message_id is not None:
            await self.redis_client.set(key, bot_message_id)
        return bot_message_id

    async def get_ticket_config_bot_channel_id(self, guild_id: int, /) -> int | None:
        key = RedisKeys.GUILD_TICKET_CONFIG_BOT_CHANNEL_ID.format(guild_id=guild_id)
        cached = await self.redis_client.get(key)
        if cached is not None:
            return int(cached)

        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, "ticket_config.bot_channel_channel_id": {"$exists": True}},
            {"ticket_config.bot_channel_channel_id": 1},
        )
        if guild is None:
            return None
        bot_channel_id = guild["ticket_config"]["bot_channel_channel_id"]
        if bot_channel_id is not None:
            await self.redis_client.set(key, bot_channel_id)
        return bot_channel_id

    async def edit_ticket_config(
        self,
        *,
        guild_id: int,
        enabled: bool | object = MISSING,
        channel_id: int | None | object = MISSING,
        use_thread: bool | object = MISSING,
        category_id: int | None | object = MISSING,
        bot_message_id: int | None | object = MISSING,
        bot_channel_channel_id: int | None | object = MISSING,
    ) -> bool:
        updates = {
            f"ticket_config.{field}": value
            for field, value in (
                ("enabled", enabled),
                ("channel_id", channel_id),
                ("use_thread", use_thread),
                ("category_id", category_id),
                ("bot_message_id", bot_message_id),
                ("bot_channel_channel_id", bot_channel_channel_id),
            )
            if value is not MISSING
        }
        if not updates:
            return False

        result = await self.guilds_collection.update_one({"_id": guild_id}, {"$set": updates}, upsert=True)
        await self.__invalidate_ticket_config_cache(guild_id)
        return result.matched_count > 0 or result.upserted_id is not None

    async def get_all_ticket_config_message_id(self):
        cursor = self.guilds_collection.find(
            {"ticket_config.bot_message_id": {"$exists": True, "$ne": None}},
            {"ticket_config.bot_message_id": 1},
        )

        async for document in cursor:
            message_id = document["ticket_config"]["bot_message_id"]
            if message_id is not None:
                yield message_id
