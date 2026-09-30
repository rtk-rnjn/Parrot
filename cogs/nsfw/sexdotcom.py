from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Literal

import aiohttp
import yarl

__all__ = ("Pin", "PinPage", "SexDotComGif", "SexDotComPics")

_log = logging.getLogger("bot.cogs.nsfw.sexdotcom")

_SITE = yarl.URL("https://www.sex.com")
_IMAGE_HOST = "https://imagex1.sx.cdn.live"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:157.0) Gecko/20100101 Firefox/157.0",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.sex.com/en/gifs",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}
_COOKIES = {
    "privacy-preferences": '{"essential":true,"analytics":true}',
    "locale": "en",
}
Order = Literal["likeCount", "publishedAt"]
Orientation = Literal["straight"]

_BLOCKED = re.compile(r"\b(teen|young|school|loli|shota|child|minor|underage|babysit)", re.I)

_CACHE_TTL = 300


@dataclass(slots=True)
class Pin:
    id: int
    title: str
    url: str
    width: int
    height: int

    @classmethod
    def from_json(cls, item: dict[str, Any]) -> Pin | None:
        uri = item.get("uri")
        if not uri or "id" not in item:
            return None
        return cls(
            id=item["id"],
            title=(item.get("title") or "").strip(),
            url=f"{_IMAGE_HOST}{uri}",
            width=item.get("width") or 0,
            height=item.get("height") or 0,
        )


@dataclass(slots=True)
class PinPage:
    pins: list[Pin]
    page: int
    pages: int
    total: int
    limit: int


@dataclass(slots=True)
class _Cached:
    at: float
    value: PinPage


class _SexDotCom:
    api_path: str

    def __init__(
        self,
        *,
        session: aiohttp.ClientSession,
        orientation: Orientation = "straight",
        filter_titles: bool = True,
    ) -> None:
        self.session = session
        self.orientation = orientation
        self.filter_titles = filter_titles
        self._cache: dict[tuple, _Cached] = {}
        _log.debug("Initialized %s", type(self).__name__)

    async def fetch(
        self,
        query: str | None = None,
        *,
        page: int = 1,
        order: Order = "likeCount",
        limit: int = 40,
    ) -> PinPage:
        key = (query and query.lower(), page, order, limit, self.orientation)
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit.at < _CACHE_TTL:
            return hit.value

        path = f"{self.api_path}/search" if query else self.api_path
        params: dict[str, Any] = {
            "sexual-orientation": self.orientation,
            "order": order,
            "page": max(1, page),
            "limit": limit,
        }
        if query:
            params["search"] = query

        url = _SITE.with_path(path)
        _log.debug("GET %s %s", url, params)
        async with self.session.get(url, params=params, headers=_HEADERS, cookies=_COOKIES) as resp:
            if resp.status == 429:
                _log.warning("Rate limited by sex.com")
            resp.raise_for_status()
            payload = await resp.json(content_type=None)

        _log.debug("Fetched %d pins from sex.com", len(payload.get("data", [])))

        pins = [p for item in payload.get("data", []) if (p := Pin.from_json(item))]
        if self.filter_titles:
            pins = [p for p in pins if not _BLOCKED.search(p.title)]

        paging = payload.get("paging") or {}
        result = PinPage(
            pins=pins,
            page=paging.get("page", page),
            pages=paging.get("numberOfPages", 1),
            total=paging.get("total", len(pins)),
            limit=paging.get("limit", limit),
        )

        self._evict()
        self._cache[key] = _Cached(time.monotonic(), result)
        return result

    def _evict(self) -> None:
        now = time.monotonic()
        for k in [k for k, v in self._cache.items() if now - v.at >= _CACHE_TTL]:
            del self._cache[k]

    async def search(self, query: str, *, page: int = 1, order: Order = "likeCount") -> list[str]:
        return [p.url for p in (await self.fetch(query, page=page, order=order)).pins]

    async def popular(self, page: int = 1) -> list[str]:
        return [p.url for p in (await self.fetch(page=page, order="likeCount")).pins]

    async def latest_pins(self, page: int = 1) -> list[str]:
        return [p.url for p in (await self.fetch(page=page, order="publishedAt")).pins]

    popular_this_week = popular_this_month = popular_this_year = popular_all_time = popular


class SexDotComGif(_SexDotCom):
    api_path = "/portal/api/gifs"


class SexDotComPics(_SexDotCom):
    api_path = "/portal/api/pics"
