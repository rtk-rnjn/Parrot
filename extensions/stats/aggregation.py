from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime

from pymongo import UpdateOne

from .events import COMMAND, MESSAGE, VOICE_INTERVAL, VOICE_START, Event
from .schema import Collections, day_start, ensure_utc, split_by_day, utcnow

TAG_FIELD = "applied_batches"


def _tagged(key: dict, inc: dict, batch_id: str, window: int, now: datetime) -> UpdateOne:
    return UpdateOne(
        {**key, TAG_FIELD: {"$ne": batch_id}},
        {"$inc": inc, "$push": {TAG_FIELD: {"$each": [batch_id], "$slice": -window}}, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )


def build_aggregate_ops(
    events: Iterable[Event],
    cols: Collections,
    batch_id: str,
    window: int,
    now: datetime | None = None,
) -> dict[str, list[UpdateOne]]:
    """Coalesce *new* (post-dedupe) events into one UpdateOne per aggregate document."""
    now = now or utcnow()
    acc: dict[str, dict[tuple, tuple[dict, defaultdict]]] = defaultdict(dict)
    span: dict[str, list[datetime]] = {}  # guild -> [first, last]

    def add(coll: str, key: dict, **inc: int) -> None:
        ident = tuple(sorted(key.items(), key=lambda kv: kv[0]))
        _, counters = acc[coll].setdefault(ident, (key, defaultdict(int)))
        for name, value in inc.items():
            counters[name] += value

    for e in events:
        ts = ensure_utc(e.ts)
        lo_hi = span.setdefault(e.guild_id, [ts, ts])
        lo_hi[0], lo_hi[1] = min(lo_hi[0], ts), max(lo_hi[1], ts)
        if e.kind == MESSAGE:
            day = day_start(ts)
            add(cols.messages_daily, {"guild_id": e.guild_id, "user_id": e.user_id, "channel_id": e.channel_id, "bucket_start": day}, count=1)
            add(cols.guild_daily, {"guild_id": e.guild_id, "bucket_start": day}, messages=1)
        elif e.kind == COMMAND:
            day, outcome = day_start(ts), e.data["outcome"]
            inc = {"attempts": 1, outcome: 1}
            if outcome != "rejected":  # only executed commands have a meaningful duration
                inc["timed"], inc["duration_ms"] = 1, e.data["duration_ms"]
            add(
                cols.commands_daily,
                {"guild_id": e.guild_id, "user_id": e.user_id, "command_name": e.data["command_name"], "bucket_start": day},
                **inc,
            )
            add(cols.guild_daily, {"guild_id": e.guild_id, "bucket_start": day}, commands=1)
        elif e.kind == VOICE_INTERVAL:
            segments = split_by_day(e.data["started_at"], e.data["ended_at"])
            for i, (day, ms) in enumerate(segments):
                add(
                    cols.voice_daily,
                    {"guild_id": e.guild_id, "user_id": e.user_id, "channel_id": e.channel_id, "bucket_start": day},
                    duration_ms=ms,
                    sessions=1 if i == 0 else 0,
                )
                add(cols.guild_daily, {"guild_id": e.guild_id, "bucket_start": day}, voice_ms=ms)

    ops: dict[str, list[UpdateOne]] = {}
    for coll, docs in acc.items():
        ops[coll] = [_tagged(key, dict(counters), batch_id, window, now) for key, counters in docs.values()]
    if span:
        # $min/$max are naturally idempotent, so no tag is needed.
        ops[cols.guild_stats] = [
            UpdateOne(
                {"guild_id": g}, {"$min": {"first_event_at": lo}, "$max": {"last_event_at": hi}, "$setOnInsert": {"created_at": now}}, upsert=True
            )
            for g, (lo, hi) in span.items()
        ]
    return ops


def build_session_ops(events: Iterable[Event], _: Collections) -> list[UpdateOne]:
    """Ordered voice-session state transitions (naturally idempotent ``$set`` operations)."""
    ops: list[UpdateOne] = []
    for event in events:
        if event.kind == VOICE_START:
            ops.append(
                UpdateOne(
                    {"guild_id": event.guild_id, "user_id": event.user_id, "state": "active"},
                    {
                        "$set": {
                            "session_id": event.data["session_id"],
                            "channel_id": event.channel_id,
                            "state": "active",
                            "started_at": event.ts,
                            "last_seen_at": event.ts,
                        }
                    },
                    upsert=True,
                )
            )
        elif event.kind == VOICE_INTERVAL:
            ops.append(UpdateOne({"session_id": event.data["session_id"]}, {"$set": {"state": "closed", "ended_at": event.data["ended_at"]}}))
    return ops
