"""Pure voice-session state machine (no Discord objects, no I/O).

Rules
-----
* A *move* closes the old interval and opens a new session -> no overlap, no double counting.
* Mute/deafen/stream changes (same channel) are ignored.
* A session's end is **never extrapolated**. Sessions that are no longer confirmed are closed
  at ``last_seen_at`` (the last heartbeat that verified presence), not at "now".
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from .events import Event, voice_interval_event, voice_start_event
from .schema import ensure_utc


@dataclass(slots=True)
class ActiveSession:
    session_id: str
    guild_id: str
    user_id: str
    channel_id: str
    started_at: datetime
    last_seen_at: datetime


class VoiceTracker:
    def __init__(self) -> None:
        self._sessions: dict[tuple[str, str], ActiveSession] = {}

    def __len__(self) -> int:
        return len(self._sessions)

    def get(self, guild_id: str, user_id: str) -> ActiveSession | None:
        return self._sessions.get((guild_id, user_id))

    def sessions(self) -> list[ActiveSession]:
        return list(self._sessions.values())

    def _open(self, guild_id: str, user_id: str, channel_id: str, now: datetime) -> tuple[ActiveSession, Event]:
        s = ActiveSession(uuid.uuid4().hex, guild_id, user_id, channel_id, now, now)
        self._sessions[(guild_id, user_id)] = s
        return s, voice_start_event(session_id=s.session_id, guild_id=guild_id, user_id=user_id, channel_id=channel_id, started_at=now)

    def _close(self, s: ActiveSession, end: datetime) -> Event:
        self._sessions.pop((s.guild_id, s.user_id), None)
        end = max(ensure_utc(end), s.started_at)  # clock skew can never yield negative time
        return voice_interval_event(
            session_id=s.session_id,
            guild_id=s.guild_id,
            user_id=s.user_id,
            channel_id=s.channel_id,
            started_at=s.started_at,
            ended_at=end,
        )

    def transition(self, guild_id: str, user_id: str, before: str | None, after: str | None, now: datetime) -> list[Event]:
        """Handle ``on_voice_state_update``. Order of returned events matters: close, then start."""
        if before == after:
            return []
        events: list[Event] = []
        current = self._sessions.get((guild_id, user_id))
        if current:
            events.append(self._close(current, now))
        if after is not None:
            events.append(self._open(guild_id, user_id, after, now)[1])
        return events

    def close_guild(self, guild_id: str, now: datetime) -> list[Event]:
        return [self._close(s, now) for s in self.sessions() if s.guild_id == guild_id]

    def close_all(self, now: datetime) -> list[Event]:
        return [self._close(s, now) for s in self.sessions()]

    def adopt(self, s: ActiveSession) -> bool:
        """Restore a persisted session unless a live one already exists for the user."""
        key = (s.guild_id, s.user_id)
        if key in self._sessions:
            return False
        self._sessions[key] = s
        return True

    def reconcile(self, guild_id: str, present: dict[str, str], now: datetime, max_gap: timedelta) -> tuple[list[Event], list[str]]:
        """Align tracked sessions with the *observed* voice states of one guild.

        ``present`` maps user_id -> channel_id for humans currently in voice.
        Returns ``(events, touched_session_ids)``; touched sessions were verified at ``now``.
        """
        events: list[Event] = []
        touched: list[str] = []
        for s in [x for x in self._sessions.values() if x.guild_id == guild_id]:
            same_channel = present.get(s.user_id) == s.channel_id
            if same_channel and now - s.last_seen_at <= max_gap:
                s.last_seen_at = now
                touched.append(s.session_id)
            else:
                # Left unobserved, or our knowledge has a gap (restart/outage): credit only up to
                # the last time presence was verified, then (below) start a fresh session.
                events.append(self._close(s, s.last_seen_at))
        for user_id, channel_id in present.items():
            if (guild_id, user_id) not in self._sessions:
                s, start = self._open(guild_id, user_id, channel_id, now)
                events.append(start)
                touched.append(s.session_id)
        return events, touched
