from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING, Any

import aiohttp
import yarl

from discord.ext import commands

if TYPE_CHECKING:
    from typing_extensions import Self


class HasteBinData:
    def __init__(self, *, key: str = None, content: str = None) -> None:
        self.key = key
        self.content = content

    @property
    def url(self) -> str:
        return f"https://hastebin.com/{self.key}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(key=data.get("key"), content=data.get("content"))


class Route:
    BASE_API = yarl.URL("https://hastebin.com")

    def __init__(self, path: str = "", **parameters: str) -> None:
        self.url = self.BASE_API
        if path:
            self.url = self.BASE_API / path
        self.url = self.url.with_query(parameters)


class HTTPClient:
    def __init__(self, *, session: aiohttp.ClientSession | None = None) -> None:
        self.session: aiohttp.ClientSession = session
        self.token = os.environ.get("HASTEBIN")
        self.__lock = asyncio.Semaphore(2)

        self.__cache = {}

    async def _generate_session(self) -> aiohttp.ClientSession:
        self.session = aiohttp.ClientSession()
        return self.session

    async def close(self) -> None:
        await self.session.close()

    async def request(self, method: str, route: Route, **kwargs: str) -> dict[str, Any]:
        if not self.session:
            await self._generate_session()

        async with self.__lock:
            for _ in range(5):
                if self.token is not None:
                    headers = {"Authorization": f"Bearer {self.token}"}
                else:
                    headers = {}
                async with self.session.request(method, route.url, headers=headers, **kwargs) as resp:
                    data = await resp.json()
                    if "message" in data:
                        await asyncio.sleep(1)
                        continue
                    return data
        msg = "Hastebin is currently down, please try again later."
        raise commands.BadArgument(msg)

    async def post(self, route: Route, **kwargs: str) -> dict[str, Any]:
        return await self.request("POST", route, **kwargs)

    async def get(self, route: Route, **kwargs: str) -> dict[str, Any]:
        return await self.request("GET", route, **kwargs)

    async def create_document(self, content: str) -> HasteBinData:
        data = await self.post(Route("documents"), data=content)
        hastebin = HasteBinData.from_dict(data)
        self.__cache[hastebin.key] = hastebin
        return hastebin

    async def fetch_document(self, key: str) -> HasteBinData:
        data = await self.get(Route(f"documents/{key}"))
        hastebin = HasteBinData.from_dict(data)
        self.__cache[hastebin.key] = hastebin
        return hastebin

    def get_document(self, key: str) -> HasteBinData | None:
        return self.__cache.get(key)

    async def get_or_fetch_document(self, key: str) -> HasteBinData:
        if (hastebin := self.get_document(key)) is not None:
            return hastebin
        return await self.fetch_document(key)
