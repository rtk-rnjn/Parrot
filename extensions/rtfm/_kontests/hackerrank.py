"""HackerRank, from the REST endpoint its own contests page uses."""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict, cast

from .base import Contest, Platform, get_json, one_line, parse_each, plain_text, utc

if TYPE_CHECKING:
    import aiohttp

API = "https://www.hackerrank.com/rest/contests/upcoming"
CONTEST_URL = "https://www.hackerrank.com/contests/{slug}"
PLACEHOLDER = "Please provide a short description of your contest"  # the default text organisers never replace


class HackerRankContest(TypedDict):
    id: int
    name: str
    slug: str
    created_at: str
    rated: bool
    started: bool
    ended: bool
    epoch_starttime: int
    epoch_endtime: int
    description: str | None
    description_html: str | None
    organization_name: NotRequired[str | None]
    organization_type: NotRequired[str | None]
    get_starttimeiso: NotRequired[str]
    get_endtimeiso: NotRequired[str]
    signup_count: NotRequired[int]
    archived: NotRequired[bool]


class HackerRankResponse(TypedDict):
    models: list[HackerRankContest]
    total: int
    page: int


def parse(item: HackerRankContest) -> Contest | None:
    if item["ended"]:
        return None
    description = item.get("description") or plain_text(item.get("description_html"))
    return Contest(
        name=item["name"],
        url=CONTEST_URL.format(slug=item["slug"]),
        start=utc(item["epoch_starttime"]),
        end=utc(item["epoch_endtime"]),
        rated="rated" if item["rated"] else "unrated",
        host=item.get("organization_name") or None,
        description="" if description.startswith(PLACEHOLDER) else one_line(plain_text(description)),
    )


async def fetch(session: aiohttp.ClientSession) -> list[Contest]:
    data = cast("HackerRankResponse", await get_json(session, API))
    return parse_each(data["models"], parse, "hackerrank")


PLATFORM = Platform(key="hackerrank", name="HackerRank", url="https://www.hackerrank.com/contests", colour=0x00EA64, fetch=fetch)
