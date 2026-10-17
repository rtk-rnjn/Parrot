"""Event records that flow through the queue. No Discord objects are retained."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

MESSAGE = "message"
COMMAND = "command"
VOICE_START = "voice_start"
VOICE_INTERVAL = "voice_interval"

LEDGERED_KINDS = frozenset({MESSAGE, COMMAND, VOICE_INTERVAL})
CRITICAL_KINDS = frozenset({VOICE_START, VOICE_INTERVAL})

OUTCOMES = ("success", "failed", "rejected")
DM_GUILD = "dm"


@dataclass(slots=True)
class Event:
    kind: str
    key: str
    guild_id: str
    user_id: str
    ts: datetime
    channel_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def ledgered(self) -> bool:
        return self.kind in LEDGERED_KINDS

    @property
    def critical(self) -> bool:
        return self.kind in CRITICAL_KINDS


def message_event(*, message_id: int, guild_id: int, user_id: int, channel_id: int, ts: datetime) -> Event:
    return Event(MESSAGE, f"msg:{message_id}", str(guild_id), str(user_id), ts, str(channel_id))


def command_event(
    *,
    message_id: int,
    edited_ts: float,
    guild_id: int | None,
    user_id: int,
    channel_id: int | None,
    command_name: str,
    outcome: str,
    duration_ms: int,
    ts: datetime,
) -> Event:
    """One event per *finished* invocation.

    The key includes the message's edit timestamp so that re-running a command by
    editing the message is a distinct invocation, while a replayed delivery is not.
    """
    if outcome not in OUTCOMES:
        msg = f"bad outcome {outcome!r}"
        raise ValueError(msg)
    return Event(
        COMMAND,
        f"cmd:{message_id}:{int(edited_ts)}",
        DM_GUILD if guild_id is None else str(guild_id),
        str(user_id),
        ts,
        None if channel_id is None else str(channel_id),
        {"command_name": command_name, "outcome": outcome, "duration_ms": max(0, int(duration_ms))},
    )


def voice_start_event(*, session_id: str, guild_id: str, user_id: str, channel_id: str, started_at: datetime) -> Event:
    return Event(VOICE_START, f"vstart:{session_id}", guild_id, user_id, started_at, channel_id, {"session_id": session_id})


def voice_interval_event(*, session_id: str, guild_id: str, user_id: str, channel_id: str, started_at: datetime, ended_at: datetime) -> Event:
    return Event(
        VOICE_INTERVAL,
        f"voice:{session_id}",
        guild_id,
        user_id,
        ended_at,
        channel_id,
        {"session_id": session_id, "started_at": started_at, "ended_at": ended_at},
    )
