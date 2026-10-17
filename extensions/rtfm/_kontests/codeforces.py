"""Codeforces, from its public ``contest.list`` API."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict, cast

from .base import Contest, Platform, get_json, one_line, parse_each, plain_text, utc

if TYPE_CHECKING:
    import aiohttp

API = "https://codeforces.com/api/contest.list"
CONTEST_URL = "https://codeforces.com/contests/{id}"
RULES = {"CF": "Codeforces rules", "IOI": "IOI rules", "ICPC": "ICPC rules"}


class CodeforcesContest(TypedDict):
    id: int
    name: str
    type: Literal["CF", "IOI", "ICPC"]
    phase: Literal["BEFORE", "CODING", "PENDING_SYSTEM_TEST", "SYSTEM_TEST", "FINISHED"]
    frozen: bool
    durationSeconds: int
    startTimeSeconds: NotRequired[int]
    relativeTimeSeconds: NotRequired[int]
    freezeDurationSeconds: NotRequired[int]
    preparedBy: NotRequired[str]
    websiteUrl: NotRequired[str]
    description: NotRequired[str]
    difficulty: NotRequired[int]
    kind: NotRequired[str]
    icpcRegion: NotRequired[str]
    country: NotRequired[str]
    city: NotRequired[str]
    season: NotRequired[str]


class CodeforcesResponse(TypedDict):
    status: Literal["OK", "FAILED"]
    result: NotRequired[list[CodeforcesContest]]
    comment: NotRequired[str]


def parse(item: CodeforcesContest) -> Contest | None:
    if item["phase"] not in ("BEFORE", "CODING"):
        return None
    start = utc(item["startTimeSeconds"]) if "startTimeSeconds" in item else None
    end = start + datetime.timedelta(seconds=item["durationSeconds"]) if start is not None else None
    return Contest(
        name=item["name"],
        url=CONTEST_URL.format(id=item["id"]),
        start=start,
        end=end,
        kind=RULES.get(item["type"], item["type"]),
        host=item.get("preparedBy"),
        description=one_line(plain_text(item.get("description"))),
    )


async def fetch(session: aiohttp.ClientSession) -> list[Contest]:
    data = cast("CodeforcesResponse", await get_json(session, API))
    if data["status"] != "OK":
        msg = data.get("comment") or "Codeforces reported a failure"
        raise RuntimeError(msg)
    return parse_each(data.get("result", []), parse, "codeforces")


PLATFORM = Platform(key="codeforces", name="Codeforces", url="https://codeforces.com/contests", colour=0x1F8ACB, fetch=fetch)
