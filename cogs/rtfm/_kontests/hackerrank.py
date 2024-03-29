from __future__ import annotations

import datetime

import aiohttp
from markdownify import markdownify as md

API = "https://www.hackerrank.com/rest/"
URL = "https://www.hackerrank.com/contests"

UPCOMING = "contests/upcoming"
PAST = "contests/past"


class HackerRankContest:
    def __init__(self, data: dict) -> None:
        self.__data = data

    @property
    def id(self) -> int:
        return self.__data["id"]

    @property
    def name(self) -> str:
        return self.__data["name"]

    @property
    def slug(self) -> str:
        return self.__data["slug"]

    @property
    def created_at(self) -> datetime.datetime:
        return datetime.datetime.strptime(self.__data["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")

    @property
    def rated(self) -> bool:
        return self.__data["rated"]

    @property
    def description(self) -> str:
        return md(self.__data["description_html"]).strip()

    @property
    def ended(self) -> bool:
        return self.__data["ended"]

    @property
    def end_time(self) -> datetime.datetime:
        epoch = self.__data["epoch_endtime"]
        return datetime.datetime.fromtimestamp(epoch)

    @property
    def start_time(self) -> datetime.datetime:
        epoch = self.__data["epoch_starttime"]
        return datetime.datetime.fromtimestamp(epoch)

    @property
    def url(self) -> str:
        return f"{URL}/{self.slug}"


class HackerRank:
    def __init__(self) -> None:
        self.__contests = []

    async def fetch(self, session: aiohttp.ClientSession | None = None) -> None:
        if session is None:
            async with aiohttp.ClientSession() as session:
                await self.fetch(session)
        else:
            async with session.get(f"{API}{UPCOMING}") as response:
                data = await response.json()
                self.__contests = [HackerRankContest(c) for c in data["models"]]

    @property
    def contests(self) -> list[HackerRankContest]:
        if not self.__contests:
            msg = "No contests found. Did you forget to fetch?"
            raise ValueError(msg)
        return self.__contests
