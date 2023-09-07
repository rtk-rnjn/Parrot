from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import aiohttp
import yarl

if TYPE_CHECKING:
    from core import Parrot

from bs4 import BeautifulSoup, Tag

from .constants import SEXDOTCOM_TAGS

__all__ = ("SexDotComGif", "SexDotComPics")


class _SexDotCom:
    url: yarl.URL
    _tags: list[str] = SEXDOTCOM_TAGS

    def __init__(self, *, session: aiohttp.ClientSession):
        self.session = session

    def _verify_tag(self, tag: str) -> bool:
        return tag.lower() in self._tags

    async def add_to_db(self, bot: Parrot) -> None:
        for tag in SEXDOTCOM_TAGS:
            for page in range(1, 10 + 1):
                links = await self.tag_search(tag, page=page)
                if links:
                    await bot.sql.executemany(
                        "INSERT INTO nsfw_links_grouped (link, type) VALUES (?, ?) ON CONFLICT DO NOTHING",
                        [(link, tag) for link in links],
                    )
                await asyncio.sleep(0.8)
        await bot.sql.commit()

    async def tag_search(self, tag: str, *, page: int | None = 1) -> list[str]:
        if not self._verify_tag(tag):
            err = "Tag {tag!r} not found"
            raise ValueError(err)
        url = self.url / tag.lower()
        if page and page > 1:
            url = url % {"page": page}
        return await self._get_images(url=url)

    async def popular_this_week(self, page: int | None = 1) -> list[str]:
        url = self.url % {"sort": "popular", "sub": "week"}
        if page and page > 1:
            url = url % {"page": page}

        return await self._get_images(url=url)

    async def popular_this_month(self, page: int | None = 1) -> list[str]:
        if page and page > 1:
            url = self.url % {"page": page}
        else:
            url = self.url
        return await self._get_images(url=url)

    async def popular_this_year(self, page: int | None = 1) -> list[str]:
        url = self.url % {"sort": "popular", "sub": "year"}
        if page and page > 1:
            url = url % {"page": page}

        return await self._get_images(url=url)

    async def popular_all_time(self, page: int | None = 1) -> list[str]:
        url = self.url % {"sort": "popular", "sub": "all"}
        if page and page > 1:
            url = url % {"page": page}

        return await self._get_images(url=url)

    async def latest_pins(self, page: int | None = 1) -> list[str]:
        url = self.url % {"sort": "latest"}
        if page and page > 1:
            url = url % {"page": page}

        return await self._get_images(url=url)

    async def get_all(self) -> list[str]:
        ls = []
        for page in range(1, 10 + 1):
            ls.extend(await self.popular_this_week(page=page))
            ls.extend(await self.popular_this_month(page=page))
            ls.extend(await self.popular_this_year(page=page))
            ls.extend(await self.popular_all_time(page=page))
            ls.extend(await self.latest_pins(page=page))

        return ls

    async def _get_images(self, *, url: str | yarl.URL) -> list[str]:
        response = await self.session.get(url, headers={"Referer": str(self.url)})
        text = await response.text()
        ls = []
        soup = BeautifulSoup(text, "lxml")
        div = soup.find("div", id="masonry_container")
        if isinstance(div, Tag):
            anchors: list[Tag] = div.find_all("a", **{"class": "image_wrapper"})
            for a in anchors:
                img: Tag = a.find("img", **{"class": "image"})
                ls.append(img["data-src"])

        return ls


class SexDotComGif(_SexDotCom):
    url = yarl.URL("https://www.sex.com/") / "gifs"


class SexDotComPics(_SexDotCom):
    url = yarl.URL("https://www.sex.com/") / "pics"
