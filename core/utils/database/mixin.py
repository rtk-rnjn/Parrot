from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from redis.asyncio import Redis

from .models import CommandConfig, Giveaway, GuildConfiguration, ModAction, UserConfiguration


class DatabaseMixin:
    """Base contract for database mixins.

    Mixins are stateless domain slices composed by ``DatabaseManager``. They
    may declare the typed collection and cache dependencies they use, expose
    readable public operations, and keep implementation helpers private.
    """

    redis_client: Redis
    mongo_client: AsyncMongoClient

    guilds_collection: AsyncCollection[GuildConfiguration]
    users_collection: AsyncCollection[UserConfiguration]

    giveaways_collection: AsyncCollection[Giveaway]
    mod_actions_collection: AsyncCollection[ModAction]

    commands_config_collection: AsyncCollection[CommandConfig]

    __slots__ = ()
