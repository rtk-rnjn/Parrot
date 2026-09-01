from __future__ import annotations

from typing import Literal

from pymongo.asynchronous.collection import AsyncCollection
from redis.asyncio import Redis

from ..cache_keys import RedisKeys
from ..models import GuildConfiguration


class _GuildAutomodMixin:
    """Guild command prefix operations."""

    redis_client: Redis
    guilds_collection: AsyncCollection[GuildConfiguration]
