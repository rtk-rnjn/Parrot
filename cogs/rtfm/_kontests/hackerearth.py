from __future__ import annotations

from markdownify import markdownify as md
import aiohttp
import datetime

API = "https://www.hackerearth.com/chrome-extension/events/"


class HackerEarthContest:
    def __init__(self, data: dict) -> None:
        self.__data = data

    @property
    def id(self) -> int:
        return self.__data["id"]

    @property
    def title(self) -> str:
        return self.__data["title"]

    @property
    def description(self) -> str:
        return md(self.__data["description"]).strip()

    @property
    def url(self) -> str:
        return self.__data["url"]

    @property
    def status(self) -> str:
        return self.__data["status"]

    @property
    def start_time(self) -> datetime.datetime:
        start_tz = self.__data["start_utc_tz"]
        return datetime.datetime.fromisoformat(start_tz)

    @property
    def end_time(self) -> datetime.datetime:
        end_tz = self.__data["end_utc_tz"]
        return datetime.datetime.fromisoformat(end_tz)

    @property
    def type(self) -> str:
        return self.__data["challenge_type"]


class HackerEarth:
    def __init__(self) -> None:
        self.__contests = []

    async def fetch(self, session: aiohttp.ClientSession | None = None) -> None:
        if session is None:
            async with aiohttp.ClientSession() as session:
                await self.fetch(session)
        else:
            async with session.get(API) as resp:
                data = await resp.json()

            self.__contests = [HackerEarthContest(contest) for contest in data]

    @property
    def contests(self) -> list[HackerEarthContest]:
        if not self.__contests:
            msg = "No contests found. Please try again later."
            raise ValueError(msg)
        return self.__contests
