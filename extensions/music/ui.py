from __future__ import annotations

import discord

from core.utils import format_clock_duration, truncate

from .models import Song

__all__ = ("describe_song", "format_progress")

PROGRESS_BAR_WIDTH = 12
MAX_TITLE_LENGTH = 80


def format_progress(position: float, length: float, *, is_stream: bool = False, width: int = PROGRESS_BAR_WIDTH) -> str:
    """A slider with timestamps. Streams and unknown lengths get no slider."""
    if is_stream:
        return f"🔴 LIVE · {format_clock_duration(position)}"
    if length <= 0:
        return format_clock_duration(position)

    ratio = min(max(position / length, 0.0), 1.0)
    filled = min(int(ratio * width), width - 1)
    bar = "▬" * filled + "🔘" + "▬" * (width - 1 - filled)
    return f"{bar} {format_clock_duration(position)} / {format_clock_duration(length)}"


def describe_song(song: Song) -> str:
    """A markdown one-liner: linked title plus author."""
    title = discord.utils.escape_markdown(truncate(song.title, MAX_TITLE_LENGTH))
    label = f"[{title}]({song.uri})" if song.uri else title
    return f"**{label}** by {discord.utils.escape_markdown(song.author)}"
