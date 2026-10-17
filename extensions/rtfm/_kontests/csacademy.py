"""CS Academy, from the state its contests page loads over XHR."""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict, cast

from .base import Contest, Platform, get_json, one_line, parse_each, plain_text, utc

if TYPE_CHECKING:
    import aiohttp

API = "https://csacademy.com/contests/"
CONTEST_URL = "https://csacademy.com/contest/{name}/"


class CSAcademyContest(TypedDict):
    id: int
    name: str
    longName: str
    description: str
    startTime: float | None
    endTime: float | None
    rated: bool
    isVisible: bool
    numRegistered: int
    parentId: int | None  # set on virtual re-runs of an older round
    systemGenerated: NotRequired[bool]  # the hourly practice sessions
    maxRating: NotRequired[int]
    scoreType: NotRequired[int]


class CSAcademyState(TypedDict):
    Contest: list[CSAcademyContest]


class CSAcademyResponse(TypedDict):
    state: CSAcademyState


def parse(item: CSAcademyContest) -> Contest | None:
    if item.get("systemGenerated") or not item["isVisible"] or item["parentId"] is not None:
        return None
    start, end = item["startTime"], item["endTime"]
    if start is None:
        return None
    rated = "rated" if item["rated"] else "unrated"
    if item["rated"] and "maxRating" in item:
        rated = f"rated to {item['maxRating']}"
    return Contest(
        name=item["longName"],
        url=CONTEST_URL.format(name=item["name"]),
        start=utc(start),
        end=utc(end) if end is not None else None,
        rated=rated,
        description=one_line(plain_text(item.get("description"))),
    )


async def fetch(session: aiohttp.ClientSession) -> list[Contest]:
    data = cast("CSAcademyResponse", await get_json(session, API, headers={"x-requested-with": "XMLHttpRequest"}))
    return parse_each(data["state"]["Contest"], parse, "csacademy")


PLATFORM = Platform(key="csacademy", name="CS Academy", url="https://csacademy.com/contests/", colour=0x29B6F6, fetch=fetch)
