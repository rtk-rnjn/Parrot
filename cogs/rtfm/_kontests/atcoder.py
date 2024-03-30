from __future__ import annotations

import datetime

import aiohttp
from bs4 import BeautifulSoup

API = "https://atcoder.jp/contests"
BASE_URL = "https://atcoder.jp"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S%z"


class AtCoderContestData:
    def __init__(self, data: dict) -> None:
        self.__data = data

    @property
    def name(self) -> str:
        return self.__data["name"].replace("\n", " ")

    @property
    def start_time(self) -> datetime.datetime:
        return datetime.datetime.strptime(self.__data["start_time"], TIME_FORMAT)

    @property
    def duration_minutes(self) -> int:
        hrs, mins = map(int, self.__data["duration"].split(":"))
        return hrs * 60 + mins

    @property
    def rated_range(self) -> str:
        return self.__data["rated_range"]

    @property
    def url(self) -> str:
        return BASE_URL + self.__data["url"]


class AtCoder:
    def __init__(self) -> None:
        self.__contests = []

    async def fetch(self, session: aiohttp.ClientSession | None = None):
        if session is None:
            async with aiohttp.ClientSession() as session:
                await self.fetch(session)
        else:
            async with session.get(API) as response:
                return BeautifulSoup(await response.text(), "html.parser")

    def _get_contest_table(self, soup):
        if div := soup.find("div", id="contest-table-upcoming"):
            return div.find("table")

        error = "Could not find the contest table"
        raise ValueError(error)

    def _parse_contest_row(self, row: BeautifulSoup) -> AtCoderContestData:
        cells = row.find_all("td")
        return AtCoderContestData(
            {
                "name": cells[1].text.strip(),
                "start_time": cells[0].text.strip(),
                "duration": cells[2].text.strip(),
                "rated_range": cells[3].text.strip(),
                "url": cells[1].find("a")["href"],
            },
        )

    def _parse_contest_table(self, table: BeautifulSoup):
        for row in table.find_all("tr")[1:]:
            contest = self._parse_contest_row(row)
            self.__contests.append(contest)

    async def _get_contests(self, session: aiohttp.ClientSession | None = None):
        if session is None:
            async with aiohttp.ClientSession() as session:
                return await self._get_contests(session)
        else:
            soup = await self.fetch(session)
            table = self._get_contest_table(soup)
            self._parse_contest_table(table)

    async def get_contests(self, session: aiohttp.ClientSession | None = None):
        if not self.__contests:
            await self._get_contests(session)

    @property
    def contests(self) -> list[AtCoderContestData]:
        if not self.__contests:
            error = "Contests have not been fetched yet"
            raise ValueError(error)

        return self.__contests
