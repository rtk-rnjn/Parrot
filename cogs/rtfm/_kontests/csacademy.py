from __future__ import annotations

import datetime

import aiohttp
from bs4 import BeautifulSoup
from markdownify import MarkdownConverter

API = "https://csacademy.com/contests/"
BASE_URL = "https://csacademy.com"


class CustomMarkdownConverter(MarkdownConverter):
    def convert_a(self, el, text, convert_as_inline):
        return f"[{text}]({BASE_URL}{el.get('href')})"


class CSAcademyContestData:
    def __init__(self, data: dict) -> None:
        self.__data = data

    @property
    def name(self) -> str:
        return self.__data["longName"]

    @property
    def start_time(self) -> datetime.datetime | None:
        if not self.__data["startTime"]:
            return None

        return datetime.datetime.fromtimestamp(self.__data["startTime"])

    @property
    def end_time(self) -> datetime.datetime | None:
        if not self.__data["endTime"]:
            return None
        return datetime.datetime.fromtimestamp(self.__data["endTime"])

    @property
    def duration_seconds(self) -> int:
        return self.__data["endTime"] - self.__data["startTime"]

    @property
    def ended(self) -> bool:
        return datetime.datetime.now() > self.end_time if self.end_time else False

    @property
    def description(self) -> str:
        soup = BeautifulSoup(self.__data["description"], "html.parser")
        for tag in soup.find_all("style"):
            tag.decompose()
        converter = CustomMarkdownConverter()
        return converter.convert(str(soup))

    @property
    def rated(self) -> bool:
        return self.__data["rated"]

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.__data['name']}"


class CSAcademy:
    def __init__(self) -> None:
        self.__contests = []

    async def fetch(self, session: aiohttp.ClientSession | None = None):
        if session is None:
            async with aiohttp.ClientSession() as session:
                await self.fetch(session)
        else:
            async with session.get(API, headers={"x-requested-with": "XMLHttpRequest"}) as response:
                return await response.json()

    async def get_contests(self, session: aiohttp.ClientSession | None = None):
        if session is None:
            async with aiohttp.ClientSession() as session:
                return await self.get_contests(session)
        else:
            data = await self.fetch(session)

            assert data is not None

            for contest in data["state"]["Contest"]:
                if contest["name"] == "archive" and contest["longName"] == "Archive":
                    continue

                self.__contests.append(CSAcademyContestData(contest))

    @property
    def contests(self) -> list[CSAcademyContestData]:
        if not self.__contests:
            error = "Contests have not been fetched yet"
            raise ValueError(error)

        return self.__contests
