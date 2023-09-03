from __future__ import annotations

import aiohttp
from bs4 import BeautifulSoup, Tag

from .constants import SEXDOTCOM_TAGS

__all__ = ("SexDotComGif", "SexDotComPics")

class _SexDotCom:
    url: str
    def __init__(self, *, session: aiohttp.ClientSession):
        self.session = session

    def _verify_tag(self, tag: str) -> bool:
        return tag.lower() in SEXDOTCOM_TAGS

    async def tag_search(self, tag: str) -> list[str]:
        if not self._verify_tag(tag):
            err = "Tag {tag!r} not found"
            raise ValueError(err)
        url = f"{self.url}/{tag.lower()}"
        return await self._get_images(url=url)

    async def popular_this_week(self) -> list[str]:
        url = f"{self.url}/?sort=popular&sub=week"
        return await self._get_images(url=url)

    async def popular_this_month(self) -> list[str]:
        return await self._get_images(url=self.url)

    async def popular_this_year(self) -> list[str]:
        url = f"{self.url}/?sort=popular&sub=year"
        return await self._get_images(url=url)

    async def popular_all_time(self) -> list[str]:
        url = f"{self.url}/?sort=popular&sub=all"
        return await self._get_images(url=url)

    async def latest_pins(self) -> list[str]:
        url = f"{self.url}/?sort=latest"
        return await self._get_images(url=url)

    async def get_all(self) -> list[str]:
        ls = []
        ls.extend(await self.popular_this_week())
        ls.extend(await self.popular_this_month())
        ls.extend(await self.popular_this_year())
        ls.extend(await self.popular_all_time())
        ls.extend(await self.latest_pins())
        return ls

    async def _get_images(self, *, url: str) -> list[str]:
        response = await self.session.get(url)
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
    url = "https://www.sex.com/gifs"


class SexDotComPics(_SexDotCom):
    url = "https://www.sex.com/pics"
