from __future__ import annotations

import asyncio
import json
import urllib.parse
from typing import Any

import aiohttp
import async_timeout

BASE_URL = "https://youtube.com"


class YoutubeSearch:
    search_terms: str

    def __init__(self, max_results: int | None = 5) -> None:
        self.max_results = max_results
        self.__initiated = False

        self._cache: dict[str, list[dict]] = {}

    async def close(self) -> None:
        if hasattr(self, "session"):
            await self.session.close()

    async def init(self) -> None:
        self.session = aiohttp.ClientSession()
        self.__initiated = True

    async def _search(self, search_term: str) -> list[dict]:
        if not self.__initiated:
            await self.init()

        self.search_terms = search_term
        encoded_search = urllib.parse.quote_plus(self.search_terms)

        url = f"{BASE_URL}/results?search_query={encoded_search}"
        http_response = await self.session.get(url)
        if http_response.status == 200:
            response: str = await http_response.text()
        else:
            return []

        if not (response := await self._get_initial_data(response=response, url=url)):
            return []

        results = self._parse_html(response)
        if self.max_results is not None and len(results) > self.max_results:
            results = results[: self.max_results]

        self._cache[self.search_terms] = results
        return results

    async def _get_initial_data(self, *, response: str, url: str) -> str:
        try:
            async with async_timeout.timeout(3):
                while "ytInitialData" not in response:
                    http_response = await self.session.get(url)
                    if http_response.status == 200:
                        response = await http_response.text()
        except asyncio.TimeoutError:
            return ""
        return response

    def _parse_html(self, response: str) -> list[dict]:
        results = []
        start = response.index("ytInitialData") + len("ytInitialData") + 3
        end = response.index("};", start) + 1
        json_str = response[start:end]
        data = json.loads(json_str)

        videos: list[dict] = data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"][
            "contents"
        ][0]["itemSectionRenderer"]["contents"]

        for video in videos:
            res = {}
            if "videoRenderer" in video.keys():
                video_data: dict[str, Any] = video.get("videoRenderer", {})
                res["id"] = video_data.get("videoId")
                res["thumbnails"] = [
                    thumb.get("url", None) for thumb in video_data.get("thumbnail", {}).get("thumbnails", [{}])
                ]
                res["title"] = video_data.get("title", {}).get("runs", [{}])[0].get("text", None)
                res["long_desc"] = video_data.get("descriptionSnippet", {}).get("runs", [{}])[0].get("text", None)
                res["channel"] = video_data.get("longBylineText", {}).get("runs", [{}])[0].get("text", None)
                res["duration"] = video_data.get("lengthText", {}).get("simpleText", 0)
                res["views"] = video_data.get("viewCountText", {}).get("simpleText", 0)
                res["publish_time"] = video_data.get("publishedTimeText", {}).get("simpleText", 0)
                res["url_suffix"] = (
                    video_data.get("navigationEndpoint", {})
                    .get("commandMetadata", {})
                    .get("webCommandMetadata", {})
                    .get("url", None)
                )
                results.append(res)
        return results

    async def to_dict(self, s: str) -> list[dict]:
        # sourcery skip: assign-if-exp, reintroduce-else, remove-unreachable-code
        if result := self._cache.get(s):
            return result
        return await self._search(s)

    async def to_json(self, s: str, **kw) -> str:
        if result := self._cache.get(s):
            return json.dumps({"videos": result}, **kw)
        return json.dumps({"videos": await self._search(s)}, **kw)


if __name__ == "__main__":

    async def main():
        search = YoutubeSearch()
        await search.init()
        # results = await search.to_json("How to make a Pizza", indent=4)
        results = await search.to_dict("How to make a discord bot")
        for data in results:
            print(type(data))
        await search.close()
        print(results)

    asyncio.run(main())
