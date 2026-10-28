"""What every contest site is reduced to, and the small helpers the site modules share."""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import aiohttp
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable

log = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Parrot/1.0 (+https://github.com/rtk-rnjn/Parrot)"}
MAX_DESCRIPTION = 160

type Status = Literal["ongoing", "upcoming", "ended"]
type Fetcher = Callable[[aiohttp.ClientSession], Awaitable[list[Contest]]]


@dataclass(frozen=True, slots=True)
class Contest:
    """One contest, the same shape whichever site it came from. Times are timezone-aware or unknown."""

    name: str
    url: str
    start: datetime.datetime | None
    end: datetime.datetime | None
    kind: str | None = None  # "Heuristic", "Hackathon", "ICPC rules"
    rated: str | None = None  # "rated", "unrated", "rated to 1999"
    host: str | None = None  # who runs it, when the site says
    description: str = ""  # one short line, already plain

    @property
    def duration(self) -> datetime.timedelta | None:
        return self.end - self.start if self.start is not None and self.end is not None else None

    def status(self, now: datetime.datetime) -> Status:
        if self.end is not None and now >= self.end:
            return "ended"
        if self.start is not None and now >= self.start:
            return "ongoing"
        return "upcoming"


@dataclass(frozen=True, slots=True)
class Platform:
    key: str
    name: str
    url: str  # the site's own contest listing
    colour: int
    fetch: Fetcher


async def get_json(session: aiohttp.ClientSession, url: str, headers: dict[str, str] | None = None) -> object:
    async with session.get(url, headers={**HEADERS, **(headers or {})}, timeout=REQUEST_TIMEOUT) as resp:
        resp.raise_for_status()
        return await resp.json(content_type=None)


async def get_text(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT) as resp:
        resp.raise_for_status()
        return await resp.text()


def parse_each[T](items: Iterable[T], parse: Callable[[T], Contest | None], platform: str) -> list[Contest]:
    """Run ``parse`` over every item, dropping the ones a site change broke instead of the whole listing."""
    contests: list[Contest] = []
    for item in items:
        try:
            contest = parse(item)
        except KeyError, TypeError, ValueError, AttributeError:
            log.warning("%s: skipping a contest the parser did not understand", platform, exc_info=True)
            continue
        if contest is not None:
            contests.append(contest)
    return contests


def utc(timestamp: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC)


def plain_text(value: str | None) -> str:
    """Sites hand descriptions over as HTML, plain text or both; keep the words only."""
    if not value:
        return ""
    page = BeautifulSoup(value, "lxml")
    for junk in page.select("style, script"):
        junk.decompose()
    return " ".join(page.get_text(" ").split())


def one_line(text: str, limit: int = MAX_DESCRIPTION) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "\N{HORIZONTAL ELLIPSIS}"
