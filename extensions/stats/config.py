"""Configuration for the statistics extension.

All values have production-safe defaults. Override them by assigning a
``StatsConfig`` (or a plain ``dict``) to ``bot.stats_config`` *before* the
extension is loaded; see ``StatsConfig.from_bot``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any


@dataclass(frozen=True, slots=True)
class StatsConfig:
    # fmt: off
    database_name: str = "database"           # only needed if it cannot be discovered
    collection_prefix: str = "stats_"               # e.g. "stats_" to namespace collections

    track_messages: bool = True
    track_voice: bool = True
    track_commands: bool = True
    include_bots: bool = False                # count bot-authored messages / bot voice time

    queue_max_size: int = 50_000              # hard bound for message/command events
    queue_critical_reserve: int = 5_000       # extra headroom reserved for voice events
    batch_size: int = 500                     # events per chunk (== per ledger insert)
    max_batches_per_flush: int = 20           # bounds one flush tick
    flush_interval_seconds: float = 5.0

    retry_attempts: int = 4                   # transient-error retries inside one flush
    retry_base_delay: float = 0.5
    retry_max_delay: float = 8.0
    max_chunk_attempts: int = 25              # flush ticks a chunk may stall before abandonment
    tag_window: int = 8                       # idempotency tags kept per aggregate document

    ledger_retention_days: int = 7            # dedupe window for replayed events
    closed_session_retention_days: int = 30
    dead_letter_retention_days: int = 30

    heartbeat_interval_seconds: float = 60.0  # reconcile + last_seen refresh cadence
    shutdown_drain_timeout: float = 20.0

    max_concurrent_renders: int = 2
    chart_cache_size: int = 64
    chart_cache_ttl_seconds: float = 120.0
    view_timeout_seconds: float = 300.0       # must stay < 15 min (interaction token life)
    leaderboard_size: int = 10
    # fmt: on

    def __post_init__(self) -> None:
        positive = (
            "queue_max_size",
            "batch_size",
            "max_batches_per_flush",
            "flush_interval_seconds",
            "retry_base_delay",
            "retry_max_delay",
            "max_chunk_attempts",
            "tag_window",
            "ledger_retention_days",
            "heartbeat_interval_seconds",
            "max_concurrent_renders",
            "chart_cache_size",
            "view_timeout_seconds",
            "leaderboard_size",
        )
        for name in positive:
            if getattr(self, name) <= 0:
                msg = f"StatsConfig.{name} must be > 0"
                raise ValueError(msg)
        if self.queue_critical_reserve < 0 or self.retry_attempts < 0:
            msg = "queue_critical_reserve / retry_attempts must be >= 0"
            raise ValueError(msg)
        if self.view_timeout_seconds >= 15 * 60:
            msg = "view_timeout_seconds must be below 900 (interaction tokens expire after 15 min)"
            raise ValueError(msg)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> StatsConfig:
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            msg = f"Unknown stats config keys: {sorted(unknown)}"
            raise ValueError(msg)
        return cls(**dict(data))

    @classmethod
    def from_bot(cls, bot: Any) -> StatsConfig:
        """Read ``bot.stats_config`` (StatsConfig or dict); fall back to defaults."""
        raw = getattr(bot, "stats_config", None)
        if raw is None:
            return cls()
        return raw if isinstance(raw, cls) else cls.from_mapping(raw)
