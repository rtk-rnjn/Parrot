from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..mixin import DatabaseMixin
from ..models import GuildConfiguration


class _GuildAutomodMixin(DatabaseMixin):
    """Guild automod configuration operations."""

    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]
