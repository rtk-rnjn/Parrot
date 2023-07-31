from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from bs4.element import Tag

from bs4 import BeautifulSoup

try:
    import lxml  # noqa: F401

    HTML_PARSER = "lxml"
except ImportError:
    HTML_PARSER = "html.parser"


class Parser:
    def __init__(self) -> None:
        self.search_params = {
            "format": "json",
            "action": "query",
            "list": "search",
        }

    async def init(self):
        self.http_session = aiohttp.ClientSession()

    async def close(self):
        await self.http_session.close()

    def _parse_snippet(self, snippet: str) -> str:
        return snippet.replace('<span class="searchmatch">', "**").replace("</span>", "**")

    async def get_wikihow(self, query: str) -> list[tuple[str, str, int]]:
        self.search_params["srsearch"] = query
        async with self.http_session.get("https://www.wikihow.com/api.php", params=self.search_params) as resp:
            data = await resp.json()

        ls = []

        if data["query"]["searchinfo"]["totalhits"] == 0:
            return ls

        if not data["query"]["search"]:
            return ls

        ls.extend(
            (search["title"], self._parse_snippet(search["snippet"]), search["pageid"]) for search in data["query"]["search"]
        )

        return ls

    async def get_wikihow_article(self, pageid: int) -> dict:
        async with self.http_session.get(
            "https://www.wikihow.com/api.php",
            params={
                "format": "json",
                "action": "parse",
                "prop": "text",
                "pageid": pageid,
                "mobileformat": "true",
            },
        ) as resp:
            data = await resp.json()

        return {
            "title": data["parse"]["title"],
            "real": self._parse_html(data["parse"]["text"]["*"]),
        }

    def _parse_html(self, html: str) -> dict:
        soup = BeautifulSoup(html, HTML_PARSER)
        with open("temp/temp.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())

        main_div: Tag = soup.find("div", {"class": "mw-parser-output"})

        if not main_div:
            return {}

        main = {}

        divs: list[Tag] = main_div.find_all("div", recursive=False)

        for div in divs:
            if "mf-section-0" in div.get("class", []):
                if para := div.find("p"):
                    main["intro"] = para.text

            head: Tag | None = div.previous_sibling  # type: ignore
            if head and head.name == "h2":
                idx = 0
                __head = self._parse_heading(head)
                main[__head] = {}
                tags_in_div: list[Tag] = div.find_all(recursive=False)

                parent_tag = None
                for tag in tags_in_div:
                    if tag.name == "h3":
                        parent_tag = self._parse_heading(tag)
                        main[__head][parent_tag] = []
                        idx += 1

                    if tag.name in {"ul", "ol"}:
                        if parent_tag:
                            main[__head][parent_tag] = self._parse_li(tag)

                        else:
                            main[__head][f"sub_head_list_{idx}"] = self._parse_list_item(tag)
                            idx += 1

                    if tag.name == "p":
                        main[__head][f"sub_head_para_{idx}"] = self._parse_list_item(tag)
                        idx += 1

                    if tag.name == "div":
                        if ls := [self._parse_list_item(li) for li in tag.find_all("li")]:
                            main[__head][f"sub_head_div_list_{idx}"] = ls
                            idx += 1

        return main

    def _parse_heading(self, heading: Tag) -> str:
        return heading.text.replace("[Edit]", "")

    def _parse_list_item(self, item: Tag) -> str:
        text = item.text

        # replace <kbd> tags with backticks
        for kbd in item.find_all("kbd"):
            text = text.replace(kbd.text, f"`{kbd.text}`")

        # replace <code> tags with triple backticks
        for code in item.find_all("code"):
            text = text.replace(code.text, f"```\n{code.text}\n```")

        # replace <b> tags with bold
        for bold in item.find_all("b"):
            text = text.replace(bold.text, f"**{bold.text}**")

        # replace <i> tags with italics
        for italic in item.find_all("i"):
            text = text.replace(italic.text, f"_{italic.text}_")

        return text.strip().replace("****", "**").strip("\n")

    def _parse_li(self, tag: Tag) -> list[list[str]] | list[str]:
        if tag.name == "ul":
            return [self._parse_list_item(li) for li in tag.find_all("li")]

        data = []
        ul, img = None, None
        if tag.name == "ol":
            for li in tag.find_all("li", recursive=False):
                temp = []
                if li.select_one("ul"):
                    ul = li.select_one("ul").extract()
                if li.select_one("img"):
                    img = li.select_one("img").extract()
                if ul:
                    temp.extend([self._parse_list_item(li) for li in ul.find_all("li")])
                    ul = None
                if img:
                    temp.append("https://www.wikihow.com" + img.get("src"))
                    img = None

                data.extend((self._parse_list_item(li), temp))
        return data
