from __future__ import annotations

import dataclasses
import enum
import itertools
import random
from collections import deque
from collections.abc import Callable, Iterable, Iterator
from typing import Any

import discord
import pomice

__all__ = ("PRESETS", "LoopMode", "Preset", "Song", "TrackQueue")

_uids = itertools.count(1)


class LoopMode(enum.Enum):
    off = "Off"
    track = "Track"
    queue = "Queue"

    @property
    def next(self) -> LoopMode:
        members = list(type(self))
        return members[(members.index(self) + 1) % len(members)]


@dataclasses.dataclass(eq=False, slots=True)
class Song:
    """A backend-agnostic track.

    Lavalink fills ``source`` with its own track. Songs resolved by yt-dlp have ``source=None``; the Lavalink
    transport resolves them lazily and the local transport streams them through FFmpeg. That is what lets a
    queue survive a switch between backends.
    """

    title: str
    author: str
    uri: str | None
    length: float  # milliseconds
    thumbnail: str | None = None
    is_stream: bool = False
    requester: discord.abc.User | None = None
    source: pomice.Track | None = None
    uid: int = dataclasses.field(default_factory=lambda: next(_uids))

    @classmethod
    def from_track(cls, track: pomice.Track, requester: discord.abc.User | None = None) -> Song:
        return cls(
            title=track.title,
            author=track.author,
            uri=track.uri,
            length=track.length,
            thumbnail=track.thumbnail,
            is_stream=track.is_stream,
            requester=requester or track.requester,
            source=track,
        )

    @property
    def search_text(self) -> str:
        return f"{self.title} {self.author}"

    def is_track(self, track: pomice.Track | None) -> bool:
        """Whether a Lavalink event's ``track`` is this song (events can arrive late)."""
        source = self.source
        return track is not None and source is not None and (source is track or source.track_id == track.track_id)


class TrackQueue:
    """A small list-backed queue with history. No pomice.Queue internals involved."""

    def __init__(self, *, history_size: int = 25) -> None:
        self._items: deque[Song] = deque()
        self.history: deque[Song] = deque(maxlen=history_size)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Song]:
        return iter(self._items)

    def __getitem__(self, index: int) -> Song:
        return self._items[index]

    def extend(self, songs: Iterable[Song]) -> None:
        self._items.extend(songs)

    def push_front(self, songs: Iterable[Song]) -> None:
        self._items.extendleft(reversed(list(songs)))

    def pop(self) -> Song | None:
        return self._items.popleft() if self._items else None

    def remove(self, index: int) -> Song:
        song = self._items[index]
        del self._items[index]
        return song

    def shuffle(self) -> None:
        items = list(self._items)
        random.shuffle(items)
        self._items = deque(items)

    def clear(self) -> None:
        self._items.clear()

    @property
    def total_length(self) -> float:
        return sum(song.length for song in self._items if not song.is_stream)


@dataclasses.dataclass(frozen=True, slots=True)
class Preset:
    """One "remix" preset. ``build`` makes Lavalink filters; ``ffmpeg`` is the equivalent ``-af`` chain used by the
    local fallback so presets keep working when Lavalink is down."""

    key: str
    label: str
    description: str
    emoji: str
    build: Callable[[], list[Any]]
    ffmpeg: str
    speed: float = 1.0


PRESETS: dict[str, Preset] = {
    preset.key: preset
    for preset in (
        Preset(
            "bassboost",
            "Bass Boost",
            "Heavier low end.",
            "\N{SPEAKER WITH THREE SOUND WAVES}",
            lambda: [pomice.Equalizer(tag="bassboost", levels=[(0, 0.3), (1, 0.25), (2, 0.2), (3, 0.1), (4, 0.05)])],
            "bass=g=8",
        ),
        Preset(
            "nightcore",
            "Nightcore",
            "Faster and higher pitched.",
            "\N{HIGH VOLTAGE SIGN}",
            lambda: [pomice.Timescale(tag="nightcore", speed=1.25, pitch=1.25, rate=1.0)],
            "aresample=48000,asetrate=60000,aresample=48000",
            speed=1.25,
        ),
        Preset(
            "vaporwave",
            "Vaporwave",
            "Slower and dreamier.",
            "\N{WATER WAVE}",
            lambda: [pomice.Timescale(tag="vaporwave", speed=0.8, pitch=0.8, rate=1.0)],
            "aresample=48000,asetrate=38400,aresample=48000",
            speed=0.8,
        ),
        Preset(
            "8d",
            "8D Audio",
            "Sound circles around your head.",
            "\N{HEADPHONE}",
            lambda: [pomice.Rotation(tag="8d", rotation_hertz=0.2)],
            "apulsator=hz=0.08",
        ),
        Preset(
            "karaoke",
            "Karaoke",
            "Pulls vocals down.",
            "\N{MICROPHONE}",
            lambda: [pomice.Karaoke(tag="karaoke", level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)],
            "stereotools=mlev=0.03",
        ),
        Preset(
            "tremolo",
            "Tremolo",
            "Pulsing volume.",
            "\N{WAVY DASH}\N{VARIATION SELECTOR-16}",
            lambda: [pomice.Tremolo(tag="tremolo", frequency=4.0, depth=0.75)],
            "tremolo=f=4:d=0.75",
        ),
        Preset(
            "soft",
            "Soft",
            "Mellow, muffled treble.",
            "\N{CLOUD}\N{VARIATION SELECTOR-16}",
            lambda: [pomice.LowPass(tag="soft", smoothing=20.0)],
            "lowpass=f=3000",
        ),
    )
}
