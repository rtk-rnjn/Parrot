"""HackerEarth, from the feed built for its browser extension."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, NotRequired, TypedDict, cast

from .base import Contest, Platform, get_json, one_line, parse_each, plain_text

if TYPE_CHECKING:
    import aiohttp

API = "https://www.hackerearth.com/chrome-extension/events/"


class HackerEarthEvent(TypedDict):
    title: str
    url: str
    status: str  # "UPCOMING" or "ONGOING"
    description: str
    challenge_type: str
    college: bool
    start_utc_tz: str  # "2026-10-05 14:30:00+00:00"
    end_utc_tz: str
    start_tz: NotRequired[str]
    end_tz: NotRequired[str]
    date: NotRequired[str]
    time: NotRequired[str]
    end_date: NotRequired[str]
    end_time: NotRequired[str]
    start_timestamp: NotRequired[str]
    end_timestamp: NotRequired[str]
    subscribe: NotRequired[str]
    thumbnail: NotRequired[str]
    cover_image: NotRequired[str]
    is_hackerearth: NotRequired[bool]


class HackerEarthResponse(TypedDict):
    response: list[HackerEarthEvent]


def parse(item: HackerEarthEvent) -> Contest | None:
    return Contest(
        name=item["title"],
        url=item["url"],
        start=datetime.datetime.fromisoformat(item["start_utc_tz"]),
        end=datetime.datetime.fromisoformat(item["end_utc_tz"]),
        kind=item.get("challenge_type") or None,
        host="college" if item.get("college") else None,
        description=one_line(plain_text(item.get("description"))),
    )


async def fetch(session: aiohttp.ClientSession) -> list[Contest]:
    data = cast("HackerEarthResponse", await get_json(session, API))
    return parse_each(data["response"], parse, "hackerearth")


PLATFORM = Platform(key="hackerearth", name="HackerEarth", url="https://www.hackerearth.com/challenges/", colour=0x2C3454, fetch=fetch)
