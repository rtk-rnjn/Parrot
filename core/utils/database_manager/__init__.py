from __future__ import annotations

import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from redis.asyncio import Redis

from .bot.stats import _BotStatsMixin
from .guild import _GuildMixin
from .models import Giveaway, GuildConfiguration, Stats, UserConfiguration
from .scam_links import _ScamLinksMixin
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
    mongo_db: object
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
    _BotStatsMixin,
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
