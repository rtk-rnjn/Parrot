from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
import random
import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pymongo import UpdateOne
from pymongo import errors as pme
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.command_cursor import AsyncCommandCursor
from pymongo.asynchronous.cursor import AsyncCursor
from pymongo.asynchronous.database import AsyncDatabase

from .aggregation import build_aggregate_ops, build_session_ops
from .config import StatsConfig
from .events import Event
from .schema import Collections, utcnow

log = logging.getLogger(__name__)
DUP_KEY = 11000


def is_transient(exc: BaseException) -> bool:
    """True for errors that justify retrying the *same* operation later."""
    if isinstance(exc, (pme.AutoReconnect, pme.ConnectionFailure, pme.ExecutionTimeout, asyncio.TimeoutError, ConnectionError, TimeoutError)):
        return True
    if isinstance(exc, pme.PyMongoError):
        return exc.has_error_label("RetryableWriteError") or exc.has_error_label("TransientTransactionError")
    return False


@dataclass(slots=True)
class Metrics:
    enqueued: int = 0
    dropped: int = 0
    flushed_events: int = 0
    duplicates_skipped: int = 0
    flushes: int = 0
    retries: int = 0
    flush_failures: int = 0
    dead_lettered: int = 0
    last_flush_seconds: float = 0.0
    last_batch_size: int = 0


@dataclass(slots=True)
class Chunk:
    id: str
    events: list[Event]
    new_events: list[Event] | None = None
    done: set[str] = field(default_factory=set)
    attempts: int = 0


async def _maybe_await[T: AsyncCursor | AsyncCommandCursor](value: T | Awaitable[T]) -> T:
    return await value if inspect.isawaitable(value) else value


class EventPipeline:
    def __init__(
        self,
        db: AsyncDatabase,
        cols: Collections,
        cfg: StatsConfig,
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._db, self._cols, self._cfg = db, cols, cfg
        self._sleep, self._clock = sleep, clock
        self._queue: deque[Event] = deque()
        self._stalled: Chunk | None = None  # at most one chunk waits for the DB
        self._lock = asyncio.Lock()  # one flusher at a time
        self.metrics = Metrics()
        self._last_drop_log = 0.0

    def enqueue(self, event: Event) -> bool:
        """Non-blocking. Returns False (and counts it) when the queue is full.

        Policy: **drop-newest with loud accounting**. Message/command events stop at
        ``queue_max_size``; voice events may use ``queue_critical_reserve`` extra slots
        because losing a session close corrupts durations.
        """
        limit = self._cfg.queue_max_size + (self._cfg.queue_critical_reserve if event.critical else 0)
        if len(self._queue) >= limit:
            self.metrics.dropped += 1
            now = time.monotonic()
            if now - self._last_drop_log > 30:
                self._last_drop_log = now
                log.error("stats queue full (%d); dropping %s events (total dropped=%d)", len(self._queue), event.kind, self.metrics.dropped)
            return False
        self._queue.append(event)
        self.metrics.enqueued += 1
        return True

    def pending(self) -> int:
        return len(self._queue) + (len(self._stalled.events) if self._stalled else 0)

    def snapshot(self):
        m = self.metrics
        return {
            "queue_size": len(self._queue),
            "stalled_events": len(self._stalled.events) if self._stalled else 0,
            "enqueued": m.enqueued,
            "dropped": m.dropped,
            "flushed": m.flushed_events,
            "duplicates_skipped": m.duplicates_skipped,
            "retries": m.retries,
            "flush_failures": m.flush_failures,
            "dead_lettered": m.dead_lettered,
            "last_flush_seconds": round(m.last_flush_seconds, 4),
            "last_batch_size": m.last_batch_size,
        }

    async def flush(self) -> int:
        """Flush up to ``max_batches_per_flush`` chunks. Safe to call concurrently."""
        async with self._lock:
            started, total = time.perf_counter(), 0
            for _ in range(self._cfg.max_batches_per_flush):
                chunk, self._stalled = self._stalled or self._next_chunk(), None
                if chunk is None:
                    break
                try:
                    await self._run_chunk(chunk)
                except asyncio.CancelledError:
                    self._stalled = chunk  # nothing is lost; tags make the re-run safe
                    raise
                except Exception as exc:
                    self.metrics.flush_failures += 1
                    chunk.attempts += 1
                    if is_transient(exc) and chunk.attempts < self._cfg.max_chunk_attempts:
                        self._stalled = chunk
                        log.warning("stats flush stalled (attempt %d, %d events kept): %r", chunk.attempts, len(chunk.events), exc)
                    else:
                        await self._abandon(chunk, exc)
                    break
                total += len(chunk.events)
                self.metrics.flushed_events += len(chunk.events)
                self.metrics.last_batch_size = len(chunk.events)
            self.metrics.flushes += 1
            self.metrics.last_flush_seconds = time.perf_counter() - started
            return total

    async def drain(self, timeout: float) -> int:
        """Flush until empty or ``timeout``. Returns the number of events still unflushed."""

        async def _loop() -> None:
            while self.pending():
                before = self.pending()
                await self.flush()
                if self.pending() >= before:
                    await asyncio.sleep(0.05)  # no progress (DB down): don't spin

        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(_loop(), timeout)
        left = self.pending()
        if left:
            log.error("stats drain timed out; %d events were NOT persisted", left)
        return left

    def _next_chunk(self) -> Chunk | None:
        if not self._queue:
            return None
        n = min(self._cfg.batch_size, len(self._queue))
        return Chunk(uuid.uuid4().hex[:12], [self._queue.popleft() for _ in range(n)])

    async def _run_chunk(self, chunk: Chunk) -> None:
        cfg = self._cfg
        for attempt in range(cfg.retry_attempts + 1):
            try:
                await self._advance(chunk)
                return
            except Exception as exc:
                if not is_transient(exc) or attempt == cfg.retry_attempts:
                    raise
                delay = min(cfg.retry_base_delay * 2**attempt, cfg.retry_max_delay)
                delay *= 1 + random.random() * 0.25
                self.metrics.retries += 1
                log.warning("transient stats write error (%r); retry %d/%d in %.2fs", exc, attempt + 1, cfg.retry_attempts, delay)
                await self._sleep(delay)

    async def _advance(self, chunk: Chunk) -> None:
        if chunk.new_events is None:
            chunk.new_events = await self._ledger_stage(chunk)
        ops = build_aggregate_ops(chunk.new_events, self._cols, chunk.id, self._cfg.tag_window)
        for name, coll_ops in ops.items():
            if name not in chunk.done:
                await self._apply_ops(name, coll_ops)
                chunk.done.add(name)
        if "sessions" not in chunk.done:
            session_ops = build_session_ops(chunk.events, self._cols)
            if session_ops:
                await self._apply_ordered(self._cols.voice_sessions, session_ops)
            chunk.done.add("sessions")

    async def _ledger_stage(self, chunk: Chunk) -> list[Event]:
        seen: set[str] = set()
        candidates = [e for e in chunk.events if e.ledgered and not (e.key in seen or seen.add(e.key))]
        if not candidates:
            return []
        now = self._clock()
        docs = [{"_id": e.key, "kind": e.kind, "guild_id": e.guild_id, "batch_id": chunk.id, "created_at": now} for e in candidates]
        ledger = self._db[self._cols.ledger]
        dup_keys: set[str] = set()
        try:
            await ledger.insert_many(docs, ordered=False)
        except pme.BulkWriteError as exc:
            errors = exc.details.get("writeErrors", [])
            if any(err.get("code") != DUP_KEY for err in errors):
                raise
            dup_keys = {docs[err["index"]]["_id"] for err in errors}
        if dup_keys:
            # Keys we inserted ourselves on an earlier (partially failed) attempt are NOT duplicates.
            rows = await self._to_list(ledger.find({"_id": {"$in": list(dup_keys)}}, {"batch_id": 1}))
            owner = {r["_id"]: r.get("batch_id") for r in rows}
            dup_keys = {k for k in dup_keys if owner.get(k) != chunk.id}
            self.metrics.duplicates_skipped += len(dup_keys)
        return [e for e in candidates if e.key not in dup_keys]

    async def _apply_ops(self, name: str, ops: list[UpdateOne]) -> None:
        """Unordered bulk write with poison isolation (safe because every op is tagged)."""
        coll = self._db[name]
        try:
            await self._bulk(name, coll, ops)
        except Exception as exc:
            if is_transient(exc):
                raise
            if len(ops) == 1:
                await self._dead_letter(name, ops[0], exc)
                return
            mid = len(ops) // 2
            await self._apply_ops(name, ops[:mid])
            await self._apply_ops(name, ops[mid:])

    async def _bulk(self, name: str, coll: AsyncCollection, ops: list[UpdateOne]) -> None:
        try:
            await coll.bulk_write(ops, ordered=False)
            return
        except pme.BulkWriteError as exc:
            errors = exc.details.get("writeErrors", [])
            if not errors:
                raise
            for err in errors:
                op = ops[err["index"]]
                if err.get("code") != DUP_KEY:
                    await self._dead_letter(name, op, RuntimeError(err.get("errmsg", "write error")))
                    continue

                try:
                    await coll.bulk_write([op], ordered=False)
                except pme.BulkWriteError as again:
                    if any(e.get("code") != DUP_KEY for e in again.details.get("writeErrors", [])):
                        raise

    async def _apply_ordered(self, name: str, ops: list[UpdateOne]) -> None:
        coll = self._db[name]
        try:
            await coll.bulk_write(ops, ordered=True)
        except Exception as exc:
            if is_transient(exc):
                raise
            for op in ops:  # isolate: ops are idempotent $set operations
                try:
                    await coll.bulk_write([op], ordered=True)
                except Exception as inner:
                    if is_transient(inner):
                        raise
                    await self._dead_letter(name, op, inner)

    async def _dead_letter(self, collection: str, op: Any, exc: BaseException) -> None:
        self.metrics.dead_lettered += 1
        log.error("stats write permanently failed for %s: %r | op=%r", collection, exc, op)
        try:
            await self._db[self._cols.dead_letter].insert_one(
                {"collection": collection, "op": repr(op)[:4000], "error": repr(exc)[:1000], "created_at": self._clock()}
            )
        except Exception:  # best effort; the log line above is the record
            log.exception("could not persist dead-letter record")

    async def _abandon(self, chunk: Chunk, exc: BaseException) -> None:
        self.metrics.dead_lettered += len(chunk.events)
        log.error("abandoning stats chunk %s (%d events) after %d attempts: %r", chunk.id, len(chunk.events), chunk.attempts, exc)
        try:
            await self._db[self._cols.dead_letter].insert_one(
                {
                    "chunk_id": chunk.id,
                    "error": repr(exc)[:1000],
                    "event_count": len(chunk.events),
                    "event_keys": [e.key for e in chunk.events[:100]],
                    "created_at": self._clock(),
                }
            )
        except Exception:
            log.exception("could not persist abandoned-chunk record")

    @staticmethod
    async def _to_list(cursor: AsyncCursor | AsyncCommandCursor | Awaitable[AsyncCursor] | Awaitable[AsyncCommandCursor]) -> list[dict]:
        cursor = await _maybe_await(cursor)
        return await cursor.to_list(None)
