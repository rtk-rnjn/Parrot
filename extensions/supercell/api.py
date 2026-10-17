from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urlencode

import aiohttp
import discord
from discord.ext import commands
from yarl import URL

if TYPE_CHECKING:
    from core import Bot

__all__ = (
    "BRAWL_STARS",
    "CLASH_OF_CLANS",
    "CLASH_ROYALE",
    "Forbidden",
    "Game",
    "ImageStore",
    "InvalidTag",
    "NotFound",
    "SupercellClient",
    "SupercellError",
    "Tag",
    "Unavailable",
    "enc",
    "normalize_tag",
    "parse_time",
)

_log = logging.getLogger(__name__)

TAG_ALPHABET = "0289PYLQGRJCUV"
_TAG_RE = re.compile(rf"[{TAG_ALPHABET}]{{3,15}}")
STALE_TTL = 86_400
_TIMEOUT = aiohttp.ClientTimeout(total=15)
IMAGE_DIRECTORY = Path(__file__).resolve().parents[2] / ".cache" / "supercell"

HTTP_OK = 200


class SupercellError(commands.CommandError):
    """A failure whose message is safe to show to the user."""


class InvalidTag(SupercellError):
    pass


class NotFound(SupercellError):
    pass


class Forbidden(SupercellError):
    pass


class Unavailable(SupercellError):
    pass


@dataclass(frozen=True, slots=True)
class Game:
    key: str
    name: str
    base_url: str
    env_var: str
    colour: discord.Colour

    @property
    def token(self) -> str | None:
        return os.environ.get(self.env_var) or None


CLASH_ROYALE = Game(
    "clash_royale",
    "Clash Royale",
    "https://proxy.royaleapi.dev/v1",
    "SUPERCELL_ROYALE_API",
    discord.Colour.from_rgb(46, 110, 220),
)
CLASH_OF_CLANS = Game(
    "clash_of_clans",
    "Clash of Clans",
    "https://cocproxy.royaleapi.dev/v1",
    "SUPERCELL_COC_API",
    discord.Colour.from_rgb(86, 160, 60),
)


BRAWL_STARS = Game(
    "brawl_stars",
    "Brawl Stars",
    "https://bsproxy.royaleapi.dev/v1",
    "SUPERCELL_BRAWL_API",
    discord.Colour.from_rgb(255, 196, 0),
)


def normalize_tag(raw: str) -> str:
    tag = raw.strip().upper().replace("O", "0").lstrip("#")
    if not _TAG_RE.fullmatch(tag):
        message = f"`{raw}` is not a valid tag."
        raise InvalidTag(message)
    return f"#{tag}"


def enc(tag: str) -> str:
    return quote(tag, safe="")


def parse_time(value: str | None) -> datetime | None:
    """Parse Supercell's ``20240101T120000.000Z`` timestamps."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%S.%fZ").replace(tzinfo=UTC)
    except ValueError:
        return None


class Tag(commands.Converter[str]):
    """Converts a player or clan tag. Raises ``BadArgument`` so optional parameters can fall through."""

    async def convert(self, ctx: commands.Context[Bot], argument: str) -> str:
        try:
            return normalize_tag(argument)
        except InvalidTag as error:
            raise commands.BadArgument(str(error)) from None


class SupercellClient:
    """Cached, rate-limited access to one Supercell API."""

    def __init__(self, bot: Bot, game: Game, *, concurrency: int = 8) -> None:
        self.bot = bot
        self.game = game
        self._gate = asyncio.Semaphore(concurrency)

    @property
    def _redis(self):
        return self.bot.database.redis_client

    def _key(self, path: str, params: dict[str, Any] | None) -> str:
        query = urlencode(sorted((params or {}).items()))
        return f"supercell:{self.game.key}:{path}?{query}"

    async def get(self, path: str, *, params: dict[str, Any] | None = None, ttl: int = 60) -> Any:
        """GET ``path``, serving fresh data from Redis and falling back to a stale copy while Supercell is down."""
        key = self._key(path, params)
        if (hit := await self._redis.get(key)) is not None:
            return json.loads(hit)

        try:
            data = await self._send("GET", path, params=params)
        except Unavailable:
            if (stale := await self._redis.get(f"{key}:stale")) is not None:
                return json.loads(stale)
            raise

        payload = json.dumps(data, separators=(",", ":"))
        async with self._redis.pipeline(transaction=False) as pipe:
            pipe.set(key, payload, ex=ttl)
            pipe.set(f"{key}:stale", payload, ex=STALE_TTL)
            await pipe.execute()
        return data

    async def post(self, path: str, body: dict[str, Any]) -> Any:
        return await self._send("POST", path, body=body)

    async def _send(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        token = self.game.token
        if token is None:
            message = f"The {self.game.name} API key is not configured."
            raise Unavailable(message)

        address = f"{self.game.base_url}{path}"
        if params:
            address = f"{address}?{urlencode(params)}"

        try:
            async with (
                self._gate,
                self.bot.http_session.request(
                    method,
                    URL(address, encoded=True),
                    json=body,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=_TIMEOUT,
                ) as response,
            ):
                status = response.status
                payload = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, ValueError) as error:
            message = f"{self.game.name} API did not respond. Try again shortly."
            raise Unavailable(message) from error

        if status == HTTP_OK:
            return payload

        reason = payload.get("reason", "") if isinstance(payload, dict) else ""
        _log.warning("%s API %s %s -> %s %s", self.game.name, method, path, status, reason)

        match status:
            case 400:
                message = "Supercell rejected that request. Check the tag or search terms."
                raise SupercellError(message)
            case 403:
                message = "Supercell denied access. The data may be private, or the API key / IP whitelist is wrong."
                raise Forbidden(message)
            case 404:
                message = "Supercell has no record of that."
                raise NotFound(message)
            case 429:
                message = f"The {self.game.name} API is rate limited right now. Try again in a moment."
                raise Unavailable(message)
            case 503:
                message = f"{self.game.name} is under maintenance. Try again later."
                raise Unavailable(message)
            case _:
                message = f"{self.game.name} API returned an unexpected error ({status})."
                raise Unavailable(message)


def _read(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


class ImageStore:
    """Two-level image cache: in-memory LRU backed by files on disk."""

    def __init__(self, bot: Bot, *, capacity: int = 256, directory: Path = IMAGE_DIRECTORY) -> None:
        self.bot = bot
        self.capacity = capacity
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self._memory: OrderedDict[str, bytes] = OrderedDict()

    async def get(self, url: str | None) -> bytes | None:
        if not url:
            return None

        if (cached := self._memory.get(url)) is not None:
            self._memory.move_to_end(url)
            return cached

        path = self.directory / f"{hashlib.sha1(url.encode(), usedforsecurity=False).hexdigest()}.img"
        data = await asyncio.to_thread(_read, path)
        if data is None:
            data = await self._download(url)
            if data is None:
                return None
            await asyncio.to_thread(path.write_bytes, data)

        self._memory[url] = data
        if len(self._memory) > self.capacity:
            self._memory.popitem(last=False)
        return data

    async def many(self, urls: list[str | None]) -> list[bytes | None]:
        return list(await asyncio.gather(*(self.get(url) for url in urls)))

    async def _download(self, url: str) -> bytes | None:
        try:
            async with self.bot.http_session.get(url, timeout=_TIMEOUT) as response:
                if response.status != HTTP_OK:
                    return None
                return await response.read()
        except TimeoutError, aiohttp.ClientError:
            return None
