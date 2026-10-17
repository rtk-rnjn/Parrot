from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
import math
import time
from collections.abc import Awaitable, Callable, Iterable
from typing import TYPE_CHECKING, Any, NamedTuple

import discord
import pomice

from core.utils import NoticeLayout as Notice

from .models import PRESETS, LoopMode, Preset, Song, TrackQueue
from .sources import stream_url

if TYPE_CHECKING:
    from discord.ext.commands import Context

    from core import Bot

    from .panel import MusicPanel

__all__ = ("LavalinkPlayer", "LocalPlayer", "MusicPlayer", "SessionMixin", "VoteResult")

_log = logging.getLogger(__name__)

VOTE_THRESHOLD = 0.5  # share of non-bot listeners that must agree
IDLE_TIMEOUT = 180  # seconds to wait with nothing queued before leaving
EMPTY_TIMEOUT = 60  # seconds to wait in an empty channel before leaving
MAX_FAILURES = 3  # consecutive Lavalink failures before failing over to local playback

type VoteSet = set[int]
type Action = Callable[[], Awaitable[object]]
type FailoverHandler = Callable[[Any, str], Awaitable[None]]


class VoteResult(NamedTuple):
    """Outcome of a vote-gated action. ``votes`` and ``required`` describe the tally after this vote."""

    passed: bool
    votes: int
    required: int


def _joined_at(member: discord.Member) -> datetime.datetime:
    return member.joined_at or discord.utils.snowflake_time(member.id)


class SessionMixin:
    """Everything that is not audio transport: queue, loop, DJ, votes, filters, idle timers, panel hooks.

    Subclasses provide the transport hooks at the bottom. Because the session state lives here and not in
    Lavalink, moving a session from one transport to another is just ``snapshot()`` + ``restore()``.
    """

    backend_name = "?"

    # Set by the cog.
    ctx: Context[Bot] | None
    text_channel: discord.abc.Messageable | None
    panel: MusicPanel | None
    failover: FailoverHandler | None

    def _init_session(self) -> None:
        self.ctx = None
        self.text_channel = None
        self.panel = None
        self.failover = None

        self.queue = TrackQueue()
        self.song: Song | None = None
        self.loop_mode = LoopMode.off
        self.volume_level = 100
        self.preset_key: str | None = None

        # Serialises every state change. Panel buttons try to take it without waiting, so a second click
        # that lands while the first is still being handled is turned away instead of queued up.
        self.lock = asyncio.Lock()
        self.last_change = 0.0  # monotonic time of the last track change
        self.failures = 0

        self._votes: dict[str, VoteSet] = {name: set() for name in ("pause", "resume", "skip", "shuffle", "stop")}
        self._idle_task: asyncio.Task[None] | None = None
        self._tasks: set[asyncio.Task[Any]] = set()
        self.torn_down = False

    @property
    def alive(self) -> bool:
        raise NotImplementedError

    @property
    def paused(self) -> bool:
        raise NotImplementedError

    @property
    def position_ms(self) -> float:
        raise NotImplementedError

    async def _start(self, song: Song, start_ms: int) -> None:
        raise NotImplementedError

    async def _halt(self) -> None:
        raise NotImplementedError

    async def _set_paused(self, paused: bool) -> None:
        raise NotImplementedError

    async def _apply_volume(self, level: int) -> None:
        raise NotImplementedError

    async def _seek(self, ms: int) -> None:
        raise NotImplementedError

    async def _apply_preset(self, preset: Preset | None) -> None:
        raise NotImplementedError

    async def _disconnect(self) -> None:
        raise NotImplementedError

    @property
    def usable(self) -> bool:
        return not self.torn_down and self.alive

    @property
    def listeners(self) -> list[discord.Member]:
        """Non-bot members in the voice channel. Empty once the player has disconnected."""
        channel = getattr(self, "channel", None)
        if channel is None:
            return []
        return [member for member in channel.members if not member.bot]

    def _can_manage(self, member: discord.Member) -> bool:
        permissions = member.guild_permissions
        return permissions.manage_guild or permissions.manage_channels or self.channel.permissions_for(member).manage_channels  # type: ignore[attr-defined]

    @property
    def dj(self) -> discord.Member | None:
        """Who controls the player without a vote.

        Preference: the longest-standing listener who can manage channels, then the member who connected the
        player if still listening, then the longest-standing listener.
        """
        listeners = self.listeners
        if not listeners:
            return None

        privileged = [member for member in listeners if self._can_manage(member)]
        if privileged:
            return min(privileged, key=_joined_at)

        if self.ctx is not None and isinstance(self.ctx.author, discord.Member) and self.ctx.author in listeners:
            return self.ctx.author

        return min(listeners, key=_joined_at)

    def is_dj(self, member: discord.Member) -> bool:
        dj = self.dj
        return dj is not None and dj.id == member.id

    def reset_votes(self) -> None:
        for votes in self._votes.values():
            votes.clear()

    def vote_count(self, name: str) -> int:
        return len(self._votes[name])

    @property
    def required_votes(self) -> int:
        return max(1, math.ceil(len(self.listeners) * VOTE_THRESHOLD))

    async def _vote(self, member: discord.Member, name: str, action: Action) -> VoteResult:
        """Run ``action`` at once for the DJ, otherwise once enough listeners have voted for it."""
        votes = self._votes[name]
        required = self.required_votes

        if not self.is_dj(member):
            votes.add(member.id)
            if len(votes) < required:
                return VoteResult(passed=False, votes=len(votes), required=required)

        votes.clear()
        await action()
        return VoteResult(passed=True, votes=required, required=required)

    async def vote_skip(self, member: discord.Member) -> VoteResult:
        return await self._vote(member, "skip", lambda: self.advance(skipped=True))

    async def vote_stop(self, member: discord.Member) -> VoteResult:
        return await self._vote(member, "stop", lambda: self.teardown("Playback stopped."))

    async def vote_pause(self, member: discord.Member) -> VoteResult:
        return await self._vote(member, "pause", lambda: self.set_paused(True))

    async def vote_resume(self, member: discord.Member) -> VoteResult:
        return await self._vote(member, "resume", lambda: self.set_paused(False))

    async def vote_shuffle(self, member: discord.Member) -> VoteResult:
        async def shuffle() -> None:
            self.queue.shuffle()

        return await self._vote(member, "shuffle", shuffle)

    async def enqueue(self, songs: Iterable[Song], *, front: bool = False) -> None:
        """Add ``songs`` and start playing if idle. Callers hold ``self.lock``."""
        songs = list(songs)
        (self.queue.push_front if front else self.queue.extend)(songs)

        if self.song is None:
            await self.advance()
        else:
            await self.refresh_panel()

    async def advance(self, *, skipped: bool = False) -> Song | None:
        """Move to the next song, honouring the loop mode. Callers hold ``self.lock``.

        A song that fails to start is dropped and the next one is tried, so one bad track never stalls the queue.
        """
        if not self.usable:
            return None

        self.reset_votes()
        previous, self.song = self.song, None

        if previous is not None:
            self.queue.history.append(previous)
            if self.loop_mode is LoopMode.track and not skipped:
                self.queue.push_front([previous])
            elif self.loop_mode is LoopMode.queue:
                self.queue.extend([previous])

        while (song := self.queue.pop()) is not None:
            if await self._begin(song):
                return song

        await self._finish()
        return None

    async def _begin(self, song: Song, *, start_ms: int = 0) -> bool:
        self.song = song
        try:
            await self._start(song, start_ms)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _log.warning("Could not start %r on %s: %s", song.title, self.backend_name, exc)
            self.song = None
            self.note_failure(str(exc))
            await self._notify(Notice.warning(f"Could not play **{discord.utils.escape_markdown(song.title)}**, skipping it.", footer=str(exc)[:200]))
            return False

        self.last_change = time.monotonic()
        self.sync_idle()
        await self.refresh_panel(new_track=True)
        return True

    async def _finish(self) -> None:
        """The queue ran dry: stop audio and wait for more before leaving."""
        self.song = None
        with contextlib.suppress(Exception):
            await self._halt()
        self.sync_idle()
        await self.refresh_panel()

    async def set_paused(self, paused: bool) -> None:
        if self.song is not None:
            await self._set_paused(paused)

    async def set_volume_level(self, level: int) -> None:
        self.volume_level = max(0, min(150, level))
        await self._apply_volume(self.volume_level)

    async def seek_to(self, ms: int) -> None:
        if self.song is not None and not self.song.is_stream:
            await self._seek(max(0, ms))

    async def set_preset(self, key: str | None) -> None:
        self.preset_key = key if key in PRESETS else None
        await self._apply_preset(PRESETS.get(self.preset_key) if self.preset_key else None)

    def note_failure(self, reason: str) -> None:
        """Count a playback failure; after too many in a row, hand the session to the fallback backend."""
        self.failures += 1
        if self.failures >= MAX_FAILURES and self.failover is not None:
            handler, self.failover = self.failover, None
            self.spawn(handler(self, reason))

    def spawn(self, coro: Awaitable[Any]) -> None:
        task = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _notify(self, notice: Notice) -> None:
        if self.text_channel is not None:
            with contextlib.suppress(discord.HTTPException):
                await self.text_channel.send(view=notice)

    async def refresh_panel(self, *, new_track: bool = False) -> None:
        panel = self.panel
        if panel is None:
            return
        try:
            await (panel.present() if new_track else panel.refresh())
        except Exception:  # pylint: disable=broad-exception-caught
            _log.exception("Could not refresh the music panel.")

    def sync_idle(self) -> None:
        """Start, replace or cancel the leave-timer so it matches what is happening right now."""
        if not self.listeners:
            self.schedule_idle(EMPTY_TIMEOUT, "Everyone left the voice channel.")
        elif self.song is None:
            self.schedule_idle(IDLE_TIMEOUT, "Nothing was queued for a while.")
        else:
            self.cancel_idle()

    def schedule_idle(self, delay: float, reason: str) -> None:
        self.cancel_idle()

        async def wait() -> None:
            await asyncio.sleep(delay)
            await self.teardown(reason)

        self._idle_task = asyncio.ensure_future(wait())

    def cancel_idle(self) -> None:
        task, self._idle_task = self._idle_task, None
        if task is not None and task is not asyncio.current_task():
            task.cancel()

    def snapshot(self) -> dict[str, Any]:
        return {
            "ctx": self.ctx,
            "text_channel": self.text_channel,
            "panel": self.panel,
            "queue": list(self.queue),
            "history": list(self.queue.history),
            "song": self.song,
            "position": self.position_ms,
            "loop_mode": self.loop_mode,
            "volume_level": self.volume_level,
            "preset_key": self.preset_key,
        }

    async def restore(self, state: dict[str, Any]) -> None:
        self.ctx = state["ctx"]
        self.text_channel = state["text_channel"]
        self.panel = state["panel"]
        self.loop_mode = state["loop_mode"]
        self.volume_level = state["volume_level"]
        self.preset_key = state["preset_key"]
        self.queue.extend(state["queue"])
        self.queue.history.extend(state["history"])

        if self.panel is not None:
            self.panel.player = self  # type: ignore[assignment]

        song: Song | None = state["song"]
        if song is None:
            await self._finish()
        elif not await self._begin(song, start_ms=int(state["position"])):
            await self.advance()

    async def detach(self) -> None:
        """Leave voice without touching session state. Used when moving the session to another backend."""
        self.torn_down = True
        self.cancel_idle()
        await self._disconnect()

    async def teardown(self, reason: str = "Session ended.") -> None:
        """Clear everything, close the panel and leave. Safe to call more than once."""
        if self.torn_down:
            return
        self.torn_down = True

        self.cancel_idle()
        self.reset_votes()
        self.queue.clear()
        self.song = None

        panel, self.panel = self.panel, None
        if panel is not None:
            await panel.close(reason)

        try:
            await self._disconnect()
        except Exception:  # pylint: disable=broad-exception-caught
            _log.exception("Could not disconnect the player cleanly.")


class LavalinkPlayer(SessionMixin, pomice.Player):
    """Audio through Lavalink: filters, low CPU, and what you want to be running normally."""

    backend_name = "Lavalink"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._init_session()
        self._preset_active = False

    @property
    def alive(self) -> bool:
        return self.is_connected and not self.is_dead

    @property
    def paused(self) -> bool:
        return self.is_paused

    @property
    def position_ms(self) -> float:
        return float(self.position)

    async def _start(self, song: Song, start_ms: int) -> None:
        track = song.source
        if track is None:  # resolved by yt-dlp earlier (for example after a fallback): let Lavalink find it now
            result = await self.node.get_tracks(song.uri or song.search_text, ctx=self.ctx, search_type=pomice.SearchType.ytsearch)
            candidates = result.tracks if isinstance(result, pomice.Playlist) else result
            track = song.source = candidates[0]  # pyright: ignore[reportOptionalSubscript]

        await self.play(track, start=start_ms)

    async def _halt(self) -> None:
        await self.stop()

    async def _set_paused(self, paused: bool) -> None:
        await self.set_pause(paused)

    async def _apply_volume(self, level: int) -> None:
        await self.set_volume(level)

    async def _seek(self, ms: int) -> None:
        await self.seek(ms)

    async def _apply_preset(self, preset: Preset | None) -> None:
        if self._preset_active:
            await self.reset_filters(fast_apply=preset is None)
            self._preset_active = False

        filters = preset.build() if preset is not None else []
        for index, item in enumerate(filters, start=1):
            await self.add_filter(item, fast_apply=index == len(filters))  # only the last one restarts the track
        self._preset_active = bool(filters)

    async def _disconnect(self) -> None:
        try:
            await self.destroy()
        except Exception:  # pylint: disable=broad-exception-caught
            _log.warning("Lavalink could not destroy the player; forcing the voice disconnect.")
            with contextlib.suppress(Exception):
                await self.disconnect(force=True)


class LocalPlayer(SessionMixin, discord.VoiceClient):
    """Audio decoded in-process with yt-dlp + FFmpeg. Heavier on the bot's CPU, but it needs no Lavalink."""

    backend_name = "Local (yt-dlp + FFmpeg)"

    def __init__(self, client: discord.Client, channel: discord.abc.Connectable) -> None:
        super().__init__(client, channel)
        self._init_session()

        self._generation = 0  # bumped whenever we stop audio ourselves so the `after` callback can be ignored
        self._offset = 0.0
        self._speed = 1.0
        self._started: float | None = None
        self._paused_at: float | None = None

    @property
    def alive(self) -> bool:
        return self.is_connected()

    @property
    def paused(self) -> bool:
        return self.is_paused()

    @property
    def position_ms(self) -> float:
        if self._started is None:
            return 0.0
        now = self._paused_at if self._paused_at is not None else time.monotonic()
        position = self._offset + (now - self._started) * 1000 * self._speed
        return min(position, self.song.length) if self.song is not None and self.song.length > 0 else position

    async def _start(self, song: Song, start_ms: int) -> None:
        url = await stream_url(song)
        preset = PRESETS.get(self.preset_key) if self.preset_key else None

        before = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        if start_ms > 0:
            before += f" -ss {start_ms / 1000:.3f}"
        options = "-vn" + (f' -af "{preset.ffmpeg}"' if preset is not None else "")

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(url, before_options=before, options=options),  # pyright: ignore[reportArgumentType]
            volume=self.volume_level / 100,
        )

        self._generation += 1
        generation = self._generation
        if self.is_playing() or self.is_paused():
            self.stop()

        self._speed = preset.speed if preset is not None else 1.0
        self._offset, self._started, self._paused_at = float(start_ms), time.monotonic(), None
        self.failures = 0
        self.play(source, after=lambda error: self._after(error, generation))

    def _after(self, error: Exception | None, generation: int) -> None:
        """Runs on the audio thread when a source ends. Hand control back to the event loop."""
        if generation == self._generation and not self.torn_down:
            asyncio.run_coroutine_threadsafe(self._finished(error, generation), self.client.loop)

    async def _finished(self, error: Exception | None, generation: int) -> None:
        if error is not None:
            _log.warning("FFmpeg stopped with an error: %s", error)

        async with self.lock:
            if generation == self._generation and not self.torn_down:
                await self.advance()

    async def _restart_at(self, ms: int) -> None:
        if self.song is None:
            return
        was_paused = self.paused
        await self._start(self.song, ms)
        if was_paused:
            self.pause()
            self._paused_at = time.monotonic()

    async def _halt(self) -> None:
        self._generation += 1
        self.stop()

    async def _set_paused(self, paused: bool) -> None:
        if paused:
            self.pause()
            self._paused_at = time.monotonic()
            return

        self.resume()
        if self._paused_at is not None and self._started is not None:
            self._started += time.monotonic() - self._paused_at
        self._paused_at = None

    async def _apply_volume(self, level: int) -> None:
        if isinstance(self.source, discord.PCMVolumeTransformer):
            self.source.volume = level / 100

    async def _seek(self, ms: int) -> None:
        await self._restart_at(ms)

    async def _apply_preset(self, preset: Preset | None) -> None:
        await self._restart_at(int(self.position_ms))

    async def _disconnect(self) -> None:
        self._generation += 1
        self.stop()
        await self.disconnect(force=True)


type MusicPlayer = LavalinkPlayer | LocalPlayer
