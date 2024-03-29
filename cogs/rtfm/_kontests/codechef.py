from __future__ import annotations

import datetime
from bs4 import BeautifulSoup
import aiohttp
from markdownify import markdownify as md
import random

API = "https://www.codechef.com/contests"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S%z"

with open(r"extra/user_agents.txt") as f:
    user_agents = f.read().split("\n")


class CodeChefContestData:
    def __init__(self, data: dict) -> None:
        self.__data = data

    @property
    def code(self) -> str:
        return self.__data["code"]

    @property
    def name(self) -> str:
        return self.__data["name"]

    @property
    def start_time(self) -> datetime.datetime:
        return datetime.datetime.strptime(self.__data["start_in"], TIME_FORMAT)

    @property
    def url(self) -> str:
        return f"{API}/{self.code}"

    @property
    def duration(self) -> str:
        return self.__data["duration"]


class CodeChef:
    def __init__(self) -> None:
        self.__contests = []

    async def fetch(self, session: aiohttp.ClientSession | None = None):
        if session is None:
            async with aiohttp.ClientSession() as session:
                await self.fetch(session)
        else:
            async with session.get(API, headers={"User-Agent": random.choice(user_agents)}) as response:
                return BeautifulSoup(await response.text(), "html.parser")

    async def get_contest(self, session: aiohttp.ClientSession | None = None):
        soup = await self.fetch(session)
        table_bodies = soup.find_all("tbody")

        on_going_contests = table_bodies[0]
        future_contests = table_bodies[1]

        for tr in on_going_contests.find_all("tr"):
            cells = tr.find_all("td")
            data = {
                "code": md(cells[0]).strip(),
                "name": md(cells[1]).strip(),
                "start": md(cells[2]).strip(),
                "duration": md(cells[3]).strip(),
                "start_in": md(cells[4]).strip(),
            }
            self.__contests.append(CodeChefContestData(data))

        for tr in future_contests.find_all("tr"):
            cells = tr.find_all("td")
            data = {
                "code": cells[0].text.strip(),
                "name": cells[1].text.strip(),
                "start": cells[2].text.strip(),
                "duration": cells[3].text.strip(),
                "start_in": cells[4].text.strip(),
            }
            self.__contests.append(CodeChefContestData(data))

    @property
    def contests(self):
        if not self.__contests:
            error = "No contests found"
            raise ValueError(error)
        return self.__contests
