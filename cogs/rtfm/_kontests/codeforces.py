from __future__ import annotations

import datetime
from typing import Literal

import aiohttp

API = "https://codeforces.com/api/contest.list"
API_GYM = "https://codeforces.com/api/contest.list?gym=true"
URL = "https://codeforces.com/contests/"


class Tree:
    def __init__(
        self,
        data: CodeForcesContestData,
        left: Tree | None = None,
        right: Tree | None = None,
    ) -> None:
        self.left = left
        self.right = right
        self.data = data


class CodeForcesContestData:
    def __init__(self, data: dict) -> None:
        self.__data = data

    @property
    def id(self) -> int:
        return self.__data["id"]

    @property
    def name(self) -> str:
        return self.__data["name"]

    @property
    def type(self) -> Literal["CF", "IOI", "ICPC"]:
        return self.__data["type"]

    @property
    def phase(
        self,
    ) -> Literal["BEFORE", "CODING", "PENDING_SYSTEM_TEST", "SYSTEM_TEST", "FINISHED"]:
        return self.__data["phase"]

    @property
    def frozen(self) -> bool:
        return self.__data["frozen"]

    @property
    def duration_seconds(self) -> int:
        return self.__data["durationSeconds"]

    @property
    def start_time(self) -> datetime.datetime | None:
        start_time = self.__data.get("startTimeSeconds")
        if start_time is not None:
            return datetime.datetime.fromtimestamp(start_time)

    @property
    def relative_time(self) -> int | None:
        return self.__data.get("relativeTimeSeconds")

    @property
    def prepared_by(self) -> str | None:
        return self.__data.get("preparedBy")

    @property
    def difficulty(self) -> int | None:
        return self.__data.get("difficulty")

    @property
    def kind(self) -> str | None:
        return self.__data.get("kind")

    @property
    def icpc_region(self) -> str | None:
        return self.__data.get("icpcRegion")

    @property
    def country(self) -> str | None:
        return self.__data.get("country")

    @property
    def city(self) -> str | None:
        return self.__data.get("city")

    @property
    def season(self) -> str | None:
        return self.__data.get("season")

    @property
    def description(self) -> str | None:
        return self.__data.get("description")

    @property
    def website_url(self) -> str | None:
        return self.__data.get("websiteUrl")

    @classmethod
    async def fetch(cls, session: aiohttp.ClientSession, contest_id: int) -> CodeForcesContestData:
        async with session.get(f"{API}?contestId={contest_id}") as response:
            data = await response.json()
            return cls(data["result"][0])

    @classmethod
    def from_dict(cls, data: dict) -> CodeForcesContestData:
        return cls(data)

    def to_dict(self) -> dict:
        return self.__data


class CodeForces:
    def __init__(self):
        self.__contests = []
        self.__gym = []
        self.__node = None

    @property
    def contests(self) -> list[CodeForcesContestData]:
        return self.__contests

    @property
    def gym(self) -> list[CodeForcesContestData]:
        return self.__gym

    async def fetch(self, session: aiohttp.ClientSession | None = None) -> None:
        if session is None:
            async with aiohttp.ClientSession() as session:
                await self.fetch(session)
        else:
            async with session.get(API) as response:
                data = await response.json()
                self.__contests = [CodeForcesContestData.from_dict(contest) for contest in data["result"]]
            async with session.get(API_GYM) as response:
                data = await response.json()
                self.__gym = [CodeForcesContestData.from_dict(contest) for contest in data["result"]]

        self.__contests.sort(key=lambda x: x.id, reverse=True)
        self.__gym.sort(key=lambda x: x.id, reverse=True)
        self.build_tree()

    def build_tree(self) -> None:
        self.__node = self.__build_tree(self.__contests)

    def __build_tree(self, contests: list[CodeForcesContestData]) -> Tree | None:
        if not contests:
            return None
        mid = len(contests) // 2
        return Tree(
            contests[mid],
            self.__build_tree(contests[:mid]),
            self.__build_tree(contests[mid + 1 :]),
        )

    def search(self, contest_id: int) -> CodeForcesContestData | None:
        return self.__search(self.__node, contest_id)

    def __search(self, node: Tree | None, contest_id: int) -> CodeForcesContestData | None:
        if node is None:
            return None
        if node.data.id == contest_id:
            return node.data
        if node.data.id < contest_id:
            return self.__search(node.right, contest_id)
        return self.__search(node.left, contest_id)

    def get_upcoming(self, include_gym: bool = False) -> list[CodeForcesContestData]:
        contests = [contest for contest in self.__contests if contest.phase == "BEFORE"]
        if include_gym:
            contests += [contest for contest in self.__gym if contest.phase == "BEFORE"]

        return contests

    def custom_search(
        self,
        *,
        phase: Literal["BEFORE", "CODING", "PENDING_SYSTEM_TEST", "SYSTEM_TEST", "FINISHED"] = None,
        gym: bool = False,
        difficulty: int | None = None,
    ) -> list[CodeForcesContestData]:
        contests = self.__gym if gym else self.__contests
        if phase is not None:
            contests = [contest for contest in contests if contest.phase == phase]
        if difficulty is not None:
            contests = [contest for contest in contests if contest.difficulty == difficulty]

        return contests

    def __iter__(self):
        return iter(self.__contests)
