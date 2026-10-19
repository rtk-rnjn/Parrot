from __future__ import annotations

import asyncio
import dataclasses
import logging
import os
import re
import shutil
from typing import TYPE_CHECKING

import discord
import pomice
from dotenv import load_dotenv

from .models import Song

load_dotenv()
try:
    if os.getenv("ENABLE_YTDL", "").lower() == "true":
        import yt_dlp
    else:
        yt_dlp = None
except ImportError:
    yt_dlp = None

if TYPE_CHECKING:
    from discord.ext.commands import Context
    from yt_dlp import _Params
    from yt_dlp.extractor.common import _InfoDict

    from core import Bot

__all__ = ("ResolveError", "Resolved", "local_available", "resolve", "stream_url")

_log = logging.getLogger(__name__)

SEARCH_ORDER = (
    pomice.SearchType.other,
    pomice.SearchType.scsearch,
    # pomice.SearchType.ytsearch,
)
URL_RE = re.compile(r"^https?://", re.IGNORECASE)
# Hosts yt-dlp cannot stream from; those songs are re-searched by "title author" instead.
UNSTREAMABLE = ("spotify.com", "music.apple.com", "deezer.com")

YTDL_OPTIONS: _Params = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": False,
    "playlistend": 50,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",  # noqa: S104
}


class ResolveError(Exception):
    """Nothing could resolve the query. ``errors`` holds what each source reported."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors) or "nothing found")
        self.errors = errors


@dataclasses.dataclass(slots=True)
class Resolved:
    songs: list[Song]
    name: str | None  # playlist name, if the query was a playlist
    via: str


def local_available() -> bool:
    """yt-dlp and an FFmpeg binary are both required for the local fallback."""
    return yt_dlp is not None and shutil.which("ffmpeg") is not None


async def resolve(bot: Bot, ctx: Context[Bot], query: str, *, limit: int = 1) -> Resolved:
    """Lavalink (three search backends), then yt-dlp. Raises :class:`ResolveError` when everything came up empty."""
    errors: list[str] = []

    resolved = await _resolve_lavalink(bot, ctx, query, limit, errors)
    if resolved is not None:
        return resolved

    if local_available():
        try:
            resolved = await _resolve_local(query, ctx.author, limit)
            if resolved is not None:
                return resolved
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _log.debug("yt-dlp could not resolve %r: %s", query, exc)
            errors.append(f"yt-dlp: {exc}")

    raise ResolveError(errors)


async def _resolve_lavalink(bot: Bot, ctx: Context[Bot], query: str, limit: int, errors: list[str]) -> Resolved | None:
    try:
        node = bot.lavalink_node_pool.get_best_node(algorithm=pomice.NodeAlgorithm.by_players)
    except pomice.NoNodesAvailable:
        errors.append("No Lavalink node is connected.")
        return None

    for search_type in SEARCH_ORDER:
        try:
            result = await node.get_tracks(query, ctx=ctx, search_type=search_type)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Lenient on purpose: any failure just moves on to the next search backend.
            _log.debug("Search for %r via %s failed: %s", query, search_type, exc)
            errors.append(str(exc))
            continue

        if isinstance(result, pomice.Playlist):
            if result.tracks:
                songs = [Song.from_track(track, ctx.author) for track in result.tracks]
                return Resolved(songs, result.name, "Lavalink")
        elif result:
            return Resolved([Song.from_track(track, ctx.author) for track in result[:limit]], None, "Lavalink")

    return None


def _extract(target: str, *, flat: bool):
    options: _Params = {**YTDL_OPTIONS, "extract_flat": "in_playlist" if flat else False}
    # This functions only run if yt-dlp is installed, so we can safely assume it is.
    if TYPE_CHECKING:
        assert yt_dlp is not None

    with yt_dlp.YoutubeDL(options) as ydl:
        return ydl.extract_info(target, download=False)


def _to_song(entry: _InfoDict, requester: discord.abc.User) -> Song | None:
    uri = entry.get("webpage_url") or entry.get("url")
    if not uri:
        return None

    thumbnails = entry.get("thumbnails") or [{}]
    return Song(
        title=entry.get("title") or "Unknown title",
        author=entry.get("uploader") or entry.get("channel") or "Unknown artist",
        uri=uri,
        length=(entry.get("duration") or 0) * 1000,
        thumbnail=entry.get("thumbnail") or thumbnails[-1].get("url"),
        is_stream=bool(entry.get("is_live")),
        requester=requester,
    )


async def _resolve_local(query: str, requester: discord.abc.User, limit: int) -> Resolved | None:
    is_url = bool(URL_RE.match(query))
    target = query if is_url else f"ytsearch{limit}:{query}"
    info = await asyncio.to_thread(_extract, target, flat=True)

    entries = [entry for entry in (info.get("entries") or [info]) if entry]
    songs = [song for entry in entries if (song := _to_song(entry, requester)) is not None]
    if not songs:
        return None

    is_playlist = is_url and info.get("entries") is not None
    return Resolved(songs if is_playlist else songs[:limit], info.get("title") if is_playlist else None, "yt-dlp")


async def stream_url(song: Song) -> str | None:
    """A fresh direct media URL for ``song`` (they expire, so this is resolved at play time)."""
    uri = song.uri
    target = uri if uri and URL_RE.match(uri) and not any(host in uri for host in UNSTREAMABLE) else f"ytsearch1:{song.search_text}"

    info = await asyncio.to_thread(_extract, target, flat=False)
    if info.get("entries"):
        info = next(entry for entry in info.get("entries", []) if entry)
    return info.get("url")
