"""Collection names, index definitions and UTC bucketing helpers.

Schema conventions
------------------
* Discord IDs are stored as **strings**; the DM pseudo-guild is ``"dm"``.
* All datetimes are timezone-aware UTC (BSON dates). Readers must pass values through
  :func:`ensure_utc` because some drivers/mocks return naive datetimes.
* ``bucket_start`` is the UTC midnight that starts the day bucket.
* Aggregate documents carry ``applied_batches`` (bounded list of idempotency tags).
* Durations are integer **milliseconds** (``duration_ms`` / ``voice_ms``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pymongo import ASCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from .config import StatsConfig

ONE_MS = timedelta(milliseconds=1)


def utcnow() -> datetime:
    return datetime.now(UTC)


def ensure_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def day_start(dt: datetime) -> datetime:
    return ensure_utc(dt).replace(hour=0, minute=0, second=0, microsecond=0)


def split_by_day(start: datetime, end: datetime) -> list[tuple[datetime, int]]:
    """Split ``[start, end)`` at UTC midnights -> ``[(bucket_start, milliseconds)]``.

    Cumulative flooring guarantees the segments sum to exactly ``floor(total_ms)``.
    """
    start, end = ensure_utc(start), ensure_utc(end)
    if end <= start:
        return []
    out: list[tuple[datetime, int]] = []
    cursor, prev_total = start, 0
    while cursor < end:
        boundary = min(day_start(cursor) + timedelta(days=1), end)
        total = (boundary - start) // ONE_MS
        out.append((day_start(cursor), total - prev_total))
        prev_total, cursor = total, boundary
    return [(d, ms) for d, ms in out if ms > 0]


class Collections:
    """Central registry of collection names (honours ``collection_prefix``)."""

    def __init__(self, prefix: str = "stats_") -> None:
        self.guild_stats = f"{prefix}guild_stats"
        self.guild_daily = f"{prefix}guild_stats_daily"
        self.messages_daily = f"{prefix}message_stats_daily"
        self.voice_daily = f"{prefix}voice_stats_daily"
        self.commands_daily = f"{prefix}command_stats_daily"
        self.voice_sessions = f"{prefix}voice_sessions"
        self.ledger = f"{prefix}analytics_ledger"
        self.dead_letter = f"{prefix}analytics_dead_letter"

    def all(self) -> list[str]:
        return list(vars(self).values())


def build_indexes(collection: Collections, cfg: StatsConfig) -> dict[str, list[IndexModel]]:
    """Index definitions, chosen from the query patterns in ``repository.py``."""
    A = ASCENDING
    day = 86_400
    return {
        collection.guild_stats: [IndexModel([("guild_id", A)], unique=True, name="uniq_guild")],
        collection.guild_daily: [IndexModel([("guild_id", A), ("bucket_start", A)], unique=True, name="uniq_guild_day")],
        # key order == (guild, user, channel, day) as specified; B serves guild/day ranges
        # (leaderboards), C serves per-channel series.
        collection.messages_daily: [
            IndexModel([("guild_id", A), ("user_id", A), ("channel_id", A), ("bucket_start", A)], unique=True, name="uniq_msg_key"),
            IndexModel([("guild_id", A), ("bucket_start", A)], name="guild_day"),
            IndexModel([("guild_id", A), ("channel_id", A), ("bucket_start", A)], name="guild_channel_day"),
        ],
        collection.voice_daily: [
            IndexModel([("guild_id", A), ("user_id", A), ("channel_id", A), ("bucket_start", A)], unique=True, name="uniq_voice_key"),
            IndexModel([("guild_id", A), ("bucket_start", A)], name="guild_day"),
            IndexModel([("guild_id", A), ("channel_id", A), ("bucket_start", A)], name="guild_channel_day"),
        ],
        collection.commands_daily: [
            IndexModel([("guild_id", A), ("user_id", A), ("command_name", A), ("bucket_start", A)], unique=True, name="uniq_cmd_key"),
            IndexModel([("guild_id", A), ("bucket_start", A)], name="guild_day"),
        ],
        collection.voice_sessions: [
            # at most one *active* session per (guild, user); closed rows are unconstrained
            IndexModel([("guild_id", A), ("user_id", A)], unique=True, name="uniq_active_session", partialFilterExpression={"state": "active"}),
            IndexModel([("session_id", A)], unique=True, name="uniq_session_id"),
            IndexModel([("ended_at", A)], name="ttl_closed_sessions", expireAfterSeconds=cfg.closed_session_retention_days * day),
        ],
        # _id is the event key, so uniqueness is implicit; the TTL bounds the dedupe window.
        collection.ledger: [IndexModel([("created_at", A)], name="ttl_ledger", expireAfterSeconds=cfg.ledger_retention_days * day)],
        collection.dead_letter: [IndexModel([("created_at", A)], name="ttl_dead_letter", expireAfterSeconds=cfg.dead_letter_retention_days * day)],
    }


async def ensure_indexes(db: AsyncDatabase, c: Collections, cfg: StatsConfig) -> None:
    """Idempotent: ``create_indexes`` is a no-op for identical existing indexes."""
    for name, models in build_indexes(c, cfg).items():
        await db[name].create_indexes(models)
