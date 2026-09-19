from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from .models import GuildConfiguration


class DatabaseMixin:
    """Base contract for database mixins.

    Mixins are stateless domain slices composed by ``DatabaseManager``. They
    may declare the typed collection and cache dependencies they use, expose
    readable public operations, and keep implementation helpers private.
    """

    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]

    __slots__ = ()
