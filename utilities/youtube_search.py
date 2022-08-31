from __future__ import annotations

import json
import urllib.parse
from typing import Any, Dict, Optional

import aiohttp  # type: ignore

BASE_URL = "https://youtube.com"


class YoutubeSearch:
    search_terms: str

    def __init__(self, max_results: Optional[int] = 5):
        self.max_results = max_results

        self._cache: Dict[str, str] = {}

    async def _search(self, search_term):
        self.search_terms = search_term
        encoded_search = urllib.parse.quote_plus(self.search_terms)

        url = f"{BASE_URL}/results?search_query={encoded_search}"
        async with aiohttp.ClientSession() as session:
            response = await session.get(url)
            if response.status == 200:
                response = await response.text()

        while "ytInitialData" not in response:
            async with aiohttp.ClientSession() as session:
                response = await session.get(url)
                if response.status == 200:
                    response = await response.text()
        results = self._parse_html(response)
        if self.max_results is not None and len(results) > self.max_results:
            results = results[: self.max_results]

        self._cache[self.search_terms] = results
        return results

    def _parse_html(self, response: str):
        results = []
        start = response.index("ytInitialData") + len("ytInitialData") + 3
        end = response.index("};", start) + 1
        json_str = response[start:end]
        data = json.loads(json_str)

        videos = data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"][
            "sectionListRenderer"
        ]["contents"][0]["itemSectionRenderer"]["contents"]

        for video in videos:
            res = {}
            if "videoRenderer" in video.keys():
                video_data: Dict[str, Any] = video.get("videoRenderer", {})
                res["id"] = video_data.get("videoId")
                res["thumbnails"] = [
                    thumb.get("url", None)
                    for thumb in video_data.get("thumbnail", {}).get("thumbnails", [{}])
                ]
                res["title"] = (
                    video_data.get("title", {}).get("runs", [[{}]])[0].get("text", None)
                )
                res["long_desc"] = (
                    video_data.get("descriptionSnippet", {})
                    .get("runs", [{}])[0]
                    .get("text", None)
                )
                res["channel"] = (
                    video_data.get("longBylineText", {})
                    .get("runs", [[{}]])[0]
                    .get("text", None)
                )
                res["duration"] = video_data.get("lengthText", {}).get("simpleText", 0)
                res["views"] = video_data.get("viewCountText", {}).get("simpleText", 0)
                res["publish_time"] = video_data.get("publishedTimeText", {}).get(
                    "simpleText", 0
                )
                res["url_suffix"] = (
                    video_data.get("navigationEndpoint", {})
                    .get("commandMetadata", {})
                    .get("webCommandMetadata", {})
                    .get("url", None)
                )
                results.append(res)
        return results

    async def to_dict(self, s: str) -> dict:
        return result if (result := self._cache.get(s)) else await self._search(s)

    async def to_json(self, s: str) -> str:
        if result := self._cache.get(s):
            return json.dumps({"videos": result})
        return json.dumps({"videos": await self._search(s)})
