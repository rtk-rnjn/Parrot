from __future__ import annotations

import asyncio
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from html import unescape

import re

from typing import Any, Callable, List, Optional, Dict


class ToAsync:
    def __init__(self, *, executor: Optional[ThreadPoolExecutor] = None) -> None:

        self.executor = executor

    def __call__(self, blocking) -> Callable:
        @wraps(blocking)
        async def wrapper(*args, **kwargs) -> Any:

            loop = asyncio.get_event_loop()
            if not self.executor:
                self.executor = ThreadPoolExecutor()

            func = partial(blocking, *args, **kwargs)

            return await loop.run_in_executor(self.executor, func)

        return wrapper


def __parse_text(st: str) -> str:
    return re.sub(r" +", " ", unescape(st).replace("\n", " "))


def parse_text(st: str) -> str:
    return __parse_text(st)


@ToAsync()
def find_one(
    soup: BeautifulSoup, name: str, **kwargs: Any
) -> Optional[str]:

    if finder := soup.find(name, kwargs):
        return __parse_text(finder.text)

    return None


@ToAsync()
def find_all(
    soup: BeautifulSoup, name: str, **kwargs: Any
) -> Optional[List[str]]:
    if finder := soup.find_all(name, kwargs):
        return [__parse_text(i.text) for i in finder]

    return []


@ToAsync()
def parse_url(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


@ToAsync()
def get_batting(soup: BeautifulSoup) -> Dict[str, Any]:
    data = [
        [
            __parse_text(i.text) for i in mini_table.find_all("td")
        ] for mini_table in soup.find_all(
                    "table", {"class": "table table-condensed"}
                )
    ]
    if not data:
        return {}
    return dict(zip(data[0], zip(data[0][10:], data[0][5:10])))


@ToAsync()
def get_bowling(soup: BeautifulSoup) -> Dict[str, Any]:
    data = [
        [
            __parse_text(i.text) for i in mini_table.find_all("td")
        ] for mini_table in soup.find_all(
                    "table", {"class": "table table-condensed"}
                )
    ]
    if not data:
        return {}
    return dict(zip(data[1], zip(data[1][10:], data[1][5:10])))