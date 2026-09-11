from __future__ import annotations

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..models import GuildConfiguration


class _GuildAutomodMixin:
    """Guild command prefix operations."""

    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]
