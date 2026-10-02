from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

import aiohttp

__all__ = ("PinPorn", "Video", "VideoPage")

_log = logging.getLogger("bot.cogs.nsfw.pinporn")

_BASE = "https://pin.porn"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:157.0) Gecko/20100101 Firefox/157.0",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{_BASE}/",
}
FILE_HEADERS = {**_HEADERS, "Accept": "*/*"}

_BLOCKED = re.compile(
    r"\b(teen|young|school|college|loli|shota|child|kid|minor|underage|babysit|"
    r"step-?(sis|bro|mom|dad|daughter|son))",
    re.I,
)
_JUNK = re.compile(r"\?{2,}")
_CACHE_TTL = 300


@dataclass(slots=True)
class Video:
    id: str
    title: str
    url: str
    thumbnail: str
    uploader: str
    rating: str
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, item: dict[str, Any]) -> Video | None:
        if not item.get("link") or not item.get("id"):
            return None
        return cls(
            id=str(item["id"]),
            title=_JUNK.sub("", item.get("title") or "").strip() or "Untitled",
            url=item["link"],
            thumbnail=item.get("screen") or "",
            uploader=(item.get("user") or {}).get("userTitle", "unknown"),
            rating=str(item.get("rating", "0")),
            tags=[t["tag"] for t in item.get("tags", []) if "tag" in t],
        )


@dataclass(slots=True)
class VideoPage:
    videos: list[Video]
    page: int
    pages: int
    total: int


class PinPorn:
    def __init__(self, *, session: aiohttp.ClientSession, filter_content: bool = True) -> None:
        self.session = session
        self.filter_content = filter_content
        self._cache: dict[tuple, tuple[float, VideoPage]] = {}

    def _allowed(self, v: Video) -> bool:
        return not (_BLOCKED.search(v.title) or any(_BLOCKED.search(t) for t in v.tags))

    async def search(self, query: str, *, page: int = 1, per_page: int = 30) -> VideoPage:
        key = (query.lower(), page, per_page)
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < _CACHE_TTL:
            return hit[1]

        params: dict[str, Any] = {"from_search": 1, "ipp": per_page, "q": query}
        if page > 1:
            params["page"] = page

        async with self.session.get(f"{_BASE}/api/searchVideos/", params=params, headers=_HEADERS) as resp:
            resp.raise_for_status()
            payload = await resp.json(content_type=None)

        videos = []
        for item in payload.get("data", []):
            video = Video.from_json(item)
            if video:
                videos.append(video)
        if self.filter_content:
            videos = [v for v in videos if self._allowed(v)]

        result = VideoPage(
            videos=videos,
            page=page,
            pages=int(payload.get("page_last") or 1),
            total=int(payload.get("page_total") or len(videos)),
        )
        now = time.monotonic()
        self._cache = {k: v for k, v in self._cache.items() if now - v[0] < _CACHE_TTL}
        self._cache[key] = (now, result)
        return result
