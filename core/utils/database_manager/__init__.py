from __future__ import annotations

import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from redis.asyncio import Redis

from .bot import _BotMixin
from .guild import _GuildMixin
from .models import Giveaway, GuildConfiguration, Stats, UserConfiguration
from .scam_links import _ScamLinksMixin
from .cache_keys import RedisKeys
from .user import _UserMixin

if TYPE_CHECKING:
    from core.bot import Parrot

__all__ = ("DatabaseManager",)

_ = load_dotenv()

MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb://admin:password@localhost:27017/",
)

CACHE_TTL_SECONDS = 3600


class _DatabaseInfraMixin:
    """Infrastructure and lifecycle methods only."""

    redis_client: Redis
    mongo_client: AsyncMongoClient
    guilds_collection: AsyncCollection[GuildConfiguration]
    users_collection: AsyncCollection[UserConfiguration]
    giveaways_collection: AsyncCollection[Giveaway]
    stats_collection: AsyncCollection[Stats]

    async def invalidate_redis(self) -> None:
        """Invalidate all Redis cache entries (useful for testing)."""
        await self.redis_client.flushdb()

    async def close(self) -> None:
        """Close the database connections."""
        await self.redis_client.close()
        await self.mongo_client.close()

    async def get_guild_configuration(self, guild_id: int, /) -> GuildConfiguration | None:
        return await self.guilds_collection.find_one({"_id": guild_id})

    async def get_user_configuration(self, user_id: int, /) -> UserConfiguration | None:
        return await self.users_collection.find_one({"_id": user_id})


class DatabaseManager(
    _DatabaseInfraMixin,
    _GuildMixin,
    _UserMixin,
    _ScamLinksMixin,
    _BotMixin,
):
    """Main database manager composed via mixin inheritance."""

    def __init__(self, bot: Parrot, /) -> None:
        self.bot = bot

        self.__redis_client: Redis = Redis(
            db=0,
            password="password",
            decode_responses=True,
            protocol=3,
        )

        # tz_aware=True returns timezone-aware datetimes.
        self.__mongo_client = AsyncMongoClient(MONGO_URI, tz_aware=True)
        self.mongo_db = self.mongo_client["database"]

        self.guilds_collection: AsyncCollection[GuildConfiguration] = self.mongo_db["guilds"]
        self.users_collection: AsyncCollection[UserConfiguration] = self.mongo_db["users"]
        self.giveaways_collection: AsyncCollection[Giveaway] = self.mongo_db["giveaways"]
        self.stats_collection: AsyncCollection[Stats] = self.mongo_db["stats"]

    @property
    def redis_client(self) -> Redis:
        return self.__redis_client

    @property
    def mongo_client(self) -> AsyncMongoClient:
        return self.__mongo_client

    async def ping_mongo_server(self) -> bool:
        """Ping the MongoDB server to check if it's reachable."""
        response = await self.mongo_client.admin.command("ping")
        return response.get("ok", 0) == 1

    async def ping_redis_server(self) -> bool:
        """Ping the Redis server to check if it's reachable."""
        return await self.redis_client.ping()

    async def is_guild_registered(self, guild_id: int, /) -> bool:
        """Check if a guild is registered in the database."""
        redis_key = RedisKeys.REGISTERED_GUILDS
        if await self.redis_client.sismember(redis_key, str(guild_id)):
            return True

        exists = await self.guilds_collection.count_documents({"_id": guild_id}, limit=1) > 0
        if exists:
            await self.redis_client.sadd(redis_key, str(guild_id))

        return exists

    async def is_user_registered(self, user_id: int, /) -> bool:
        """Check if a user is registered in the database."""
        redis_key = RedisKeys.REGISTERED_USERS
        if await self.redis_client.sismember(redis_key, str(user_id)):
            return True

        exists = await self.users_collection.count_documents({"_id": user_id}, limit=1) > 0
        if exists:
            await self.redis_client.sadd(redis_key, str(user_id))

        return exists

    async def register_guild(self, guild_id: int, /) -> None:
        """Register a guild in the database."""
        if not await self.is_guild_registered(guild_id):
            await self.guilds_collection.insert_one(self.empty_guild_config(guild_id))
            await self.redis_client.sadd(RedisKeys.REGISTERED_GUILDS, str(guild_id))

    async def register_user(self, user_id: int, /) -> None:
        """Register a user in the database."""
        if not await self.is_user_registered(user_id):
            await self.users_collection.insert_one(self.empty_user_config(user_id))
            await self.redis_client.sadd(RedisKeys.REGISTERED_USERS, str(user_id))
