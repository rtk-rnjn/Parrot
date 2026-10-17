"""AtCoder, scraped from the contest tables on its contests page; there is no API."""

from __future__ import annotations

import asyncio
import datetime
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup, Tag

from .base import Contest, Platform, get_text, parse_each

if TYPE_CHECKING:
    import aiohttp

BASE = "https://atcoder.jp"
TABLES = ("contest-table-upcoming", "contest-table-daily")  # the "Active Contests" block carries no table id
MIN_CELLS = 4  # start, name, duration, rated range


def rated_range(cell: str) -> str:
    """AtCoder writes the rated range as `All`, `-`, `- 1999`, `1200 -` or `1200 - 2799`."""
    text = " ".join(cell.split())
    if text in ("-", ""):
        return "unrated"
    if text.lower() == "all":
        return "rated for all"
    low, _, high = (part.strip() for part in text.partition("-"))
    if low and high:
        return f"rated {low} to {high}"
    return f"rated to {high}" if high else f"rated from {low}"


def parse_row(row: Tag) -> Contest | None:
    cells = row.find_all("td")
    if len(cells) < MIN_CELLS:
        return None
    link = cells[1].find("a")
    if not isinstance(link, Tag):
        return None
    href = link.get("href")
    start = datetime.datetime.strptime(cells[0].get_text(strip=True), "%Y-%m-%d %H:%M:%S%z")  # "2026-10-17 21:00:00+0900"
    hours, _, minutes = cells[2].get_text(strip=True).partition(":")
    duration = datetime.timedelta(hours=int(hours or 0), minutes=int(minutes or 0))
    kind = next((str(title) for span in cells[1].find_all("span") if (title := span.get("title"))), None)
    return Contest(
        name=link.get_text(" ", strip=True),
        url=f"{BASE}{href}" if isinstance(href, str) else BASE,
        start=start,
        end=start + duration,
        kind=kind,
        rated=rated_range(cells[3].get_text(strip=True)),
    )


def parse_page(html: str) -> list[Contest]:
    page = BeautifulSoup(html, "lxml")
    rows: list[Tag] = []
    for table_id in TABLES:
        block = page.find("div", id=table_id)
        if isinstance(block, Tag):
            rows.extend(row for row in block.select("table tr") if row.find("td") is not None)
    return parse_each(rows, parse_row, "atcoder")


async def fetch(session: aiohttp.ClientSession) -> list[Contest]:
    html = await get_text(session, f"{BASE}/contests/")
    return await asyncio.to_thread(parse_page, html)


PLATFORM = Platform(key="atcoder", name="AtCoder", url=f"{BASE}/contests/", colour=0x3D3D3D, fetch=fetch)
