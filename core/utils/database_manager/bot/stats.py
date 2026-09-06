from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from pymongo import UpdateOne
from pymongo.asynchronous.collection import AsyncCollection

from ..models import Stats


class _BotStatsMixin:
    stats_collection: AsyncCollection[Stats]

    async def get_stats_since(self, since: datetime, *, guild_id: int | None = None) -> list[Stats]:
        """Return aggregate stats buckets retained since ``since``."""
        query: dict[str, object] = {"interval_start": {"$gte": since}}
        if guild_id is not None:
            query["guild_id"] = guild_id

        cursor = self.stats_collection.find(query).sort("interval_start", 1)
        return [record async for record in cursor]

    async def flush_stats(self, records: Iterable[dict[str, Any]]) -> int:
        """Merge one interval of in-memory statistics into MongoDB."""
        operations = []
        for record in records:
            values = record["values"]
            identity = {
                field: record[field] for field in ("interval_start", "guild_id", "user_id", "kind", "event", "channel_id", "status", "voice_state")
            }
            metadata = {
                field: record[field]
                for field in ("_id", "interval_start", "guild_id", "user_id", "kind", "event", "channel_id", "status", "voice_state")
            }
            operations.append(
                UpdateOne(
                    identity,
                    {"$setOnInsert": metadata, "$inc": {f"values.{name}": value for name, value in values.items()}},
                    upsert=True,
                ),
            )

        if not operations:
            return 0

        await self.stats_collection.bulk_write(operations, ordered=False)
        return len(operations)
