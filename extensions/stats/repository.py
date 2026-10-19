"""Read side: narrow, indexed queries over the pre-aggregated collections.

Every query filters on ``guild_id`` first (guild isolation) and on ``bucket_start`` ranges.
Nothing here touches raw events; leaderboards ``$group`` over daily aggregates only.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from pymongo.asynchronous.command_cursor import AsyncCommandCursor
from pymongo.asynchronous.cursor import AsyncCursor
from pymongo.asynchronous.database import AsyncDatabase

from .schema import Collections, day_start, ensure_utc

DAY = timedelta(days=1)


@dataclass(frozen=True, slots=True)
class Period:
    key: str
    label: str
    days: int | None

    def bounds(self, now: datetime) -> tuple[datetime | None, datetime]:
        """``[start, end)`` in UTC. 7d == today plus the previous six UTC days."""
        end = day_start(now) + DAY
        return (None if self.days is None else end - self.days * DAY), end

    def __repr__(self) -> str:
        return f"Period({self.key!r}, {self.label!r}, {self.days!r})"

    def __str__(self) -> str:
        return self.label


PERIODS: dict[str, Period] = {
    "7d": Period("7d", "Last 7 days", 7),
    "30d": Period("30d", "Last 30 days", 30),
    "all": Period("all", "All time", None),
}
DEFAULT_PERIOD = PERIODS["7d"]

# metric -> (daily collection attr, summed field)
_METRIC = {"messages": ("messages_daily", "count"), "voice": ("voice_daily", "duration_ms")}


def _range(guild_id: str, start: datetime | None, end: datetime, **extra: Any) -> dict:
    window: dict[str, Any] = {"$lt": end}
    if start is not None:
        window["$gte"] = start
    return {"guild_id": str(guild_id), **extra, "bucket_start": window}


class StatsRepository:
    def __init__(self, db: AsyncDatabase, cols: Collections) -> None:
        self.database, self.collection = db, cols

    @staticmethod
    async def _rows(
        result: AsyncCommandCursor | Awaitable[AsyncCommandCursor] | AsyncCursor | Awaitable[AsyncCursor],
        length: int | None = None,
    ) -> list[dict]:
        if inspect.isawaitable(result):
            result = await result
        return await result.to_list(length)

    async def _aggregate(self, collection: str, pipeline: list[dict]) -> list[dict]:
        return await self._rows(self.database[collection].aggregate(pipeline))

    async def guild_daily(self, guild_id: str, start: datetime | None, end: datetime) -> list[dict]:
        cur = self.database[self.collection.guild_daily].find(_range(guild_id, start, end), {"_id": 0}).sort("bucket_start", 1).limit(4000)
        rows = await self._rows(cur)
        for r in rows:
            r["bucket_start"] = ensure_utc(r["bucket_start"])
        return rows

    async def first_event_at(self, guild_id: str) -> datetime | None:
        doc = await self.database[self.collection.guild_stats].find_one({"guild_id": str(guild_id)})
        return ensure_utc(doc["first_event_at"]) if doc and doc.get("first_event_at") else None

    async def top(
        self,
        guild_id: str,
        metric: str,
        by: str,
        start: datetime | None,
        end: datetime,
        *,
        limit: int = 10,
        skip: int = 0,
        user_id: str | None = None,
        channel_id: str | None = None,
    ) -> list[tuple[str, int]]:
        """Top ``by`` ('user_id' | 'channel_id') for ``metric`` ('messages' | 'voice')."""
        attr, field = _METRIC[metric]
        extra = {k: v for k, v in (("user_id", user_id), ("channel_id", channel_id)) if v}
        rows = await self._aggregate(
            getattr(self.collection, attr),
            [
                {"$match": _range(guild_id, start, end, **extra)},
                {"$group": {"_id": f"${by}", "v": {"$sum": f"${field}"}}},
                {"$sort": {"v": -1, "_id": 1}},
                {"$skip": skip},
                {"$limit": limit},
            ],
        )
        return [(r["_id"], int(r["v"])) for r in rows]

    async def top_commands(
        self,
        guild_id: str,
        start: datetime | None,
        end: datetime,
        *,
        limit: int = 10,
        skip: int = 0,
        user_id: str | None = None,
    ) -> list[dict]:
        extra = {"user_id": user_id} if user_id else {}
        rows = await self._aggregate(
            self.collection.commands_daily,
            [
                {"$match": _range(guild_id, start, end, **extra)},
                {
                    "$group": {
                        "_id": "$command_name",
                        "attempts": {"$sum": "$attempts"},
                        "success": {"$sum": "$success"},
                        "failed": {"$sum": "$failed"},
                        "rejected": {"$sum": "$rejected"},
                        "timed": {"$sum": "$timed"},
                        "duration_ms": {"$sum": "$duration_ms"},
                    }
                },
                {"$sort": {"attempts": -1, "_id": 1}},
                {"$skip": skip},
                {"$limit": limit},
            ],
        )
        return [
            {"command": r["_id"], **{k: int(r.get(k, 0)) for k in ("attempts", "success", "failed", "rejected", "timed", "duration_ms")}}
            for r in rows
        ]

    async def series(
        self,
        guild_id: str,
        metric: str,
        start: datetime | None,
        end: datetime,
        *,
        user_id: str | None = None,
        channel_id: str | None = None,
    ) -> list[tuple[datetime, int]]:
        """Daily totals for messages | voice | commands, optionally scoped to a user/channel."""
        if metric == "commands":
            coll, field = self.collection.commands_daily, "attempts"
        else:
            attr, field = _METRIC[metric]
            coll = getattr(self.collection, attr)
        extra = {k: v for k, v in (("user_id", user_id), ("channel_id", channel_id)) if v}
        rows = await self._aggregate(
            coll,
            [
                {"$match": _range(guild_id, start, end, **extra)},
                {"$group": {"_id": "$bucket_start", "v": {"$sum": f"${field}"}}},
                {"$sort": {"_id": 1}},
            ],
        )
        return [(ensure_utc(r["_id"]), int(r["v"])) for r in rows]

    async def totals(
        self,
        guild_id: str,
        start: datetime | None,
        end: datetime,
        *,
        user_id: str | None = None,
        channel_id: str | None = None,
    ) -> dict[str, int]:
        """messages / voice_ms / commands / failed / rejected for the scope (guild, user or channel)."""
        extra = {k: v for k, v in (("user_id", user_id), ("channel_id", channel_id)) if v}
        filter_criteria = {"$match": _range(guild_id, start, end, **extra)}

        async def total(coll: str, **fields: str) -> dict[str, int]:
            rows = await self._aggregate(coll, [filter_criteria, {"$group": {"_id": None, **{k: {"$sum": f"${v}"} for k, v in fields.items()}}}])
            return {k: int(rows[0][k]) if rows else 0 for k in fields}

        out = {
            **await total(self.collection.messages_daily, messages="count"),
            **await total(self.collection.voice_daily, voice_ms="duration_ms"),
        }
        if channel_id is None:
            out.update(await total(self.collection.commands_daily, commands="attempts", success="success", failed="failed", rejected="rejected"))
        return out
