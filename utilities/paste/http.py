from __future__ import annotations

import asyncio
import datetime
import json
import logging
import sys
import weakref
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Coroutine,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
)
from urllib.parse import quote as _uriquote

import aiohttp

from .errors import APIException
from .utils import MISSING


if TYPE_CHECKING:
    from types import TracebackType

    from .paste import File

    T = TypeVar("T")
    Response = Coroutine[None, None, T]
    MU = TypeVar("MU", bound="MaybeUnlock")
    BE = TypeVar("BE", bound=BaseException)
    from .types.responses import EditPasteResponse, PasteResponse

HTTPVerb = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]

LOGGER: logging.Logger = logging.getLogger(__name__)

__all__ = ("HTTPClient",)


def _clean_dt(dt: datetime.datetime) -> str:
    dt = dt.astimezone(datetime.timezone.utc)

    return dt.isoformat()


async def json_or_text(response: aiohttp.ClientResponse, /) -> Union[dict[str, Any], str]:
    """A quick method to parse a `aiohttp.ClientResponse` and test if it's json or text."""
    text = await response.text(encoding="utf-8")
    try:
        if response.headers["content-type"] == "application/json":
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
    except KeyError:
        pass

    return text


class MaybeUnlock:
    def __init__(self, lock: asyncio.Lock) -> None:
        self.lock: asyncio.Lock = lock
        self._unlock: bool = True

    def __enter__(self: MU) -> MU:
        return self

    def defer(self) -> None:
        self._unlock = False

    def __exit__(
        self,
        exc_type: Optional[Type[BE]],
        exc: Optional[BE],
        traceback: Optional[TracebackType],
    ) -> None:
        if self._unlock:
            self.lock.release()


class Route:
    __slots__ = (
        "verb",
        "path",
        "url",
    )

    API_BASE: ClassVar[str] = "https://api.mystb.in"

    def __init__(self, verb: HTTPVerb, path: str, **params: Any) -> None:
        self.verb: HTTPVerb = verb
        self.path: str = path
        url = self.API_BASE + path
        if params:
            url = url.format_map({k: _uriquote(v) if isinstance(v, str) else v for k, v in params.items()})
        self.url: str = url


class HTTPClient:
    __slots__ = (
        "_session",
        "_async",
        "_token",
        "_locks",
        "user_agent",
    )

    def __init__(self, *, token: Optional[str], session: Optional[aiohttp.ClientSession] = None) -> None:
        self._token: Optional[str] = token
        self._session: Optional[aiohttp.ClientSession] = session
        self._locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()
        user_agent = "mystbin.py (https://github.com/PythonistaGuild/mystbin.py) Python/{0[0]}.{0[1]} aiohttp/{1}"
        self.user_agent: str = user_agent.format(sys.version_info, aiohttp.__version__)

    async def close(self) -> None:
        if self._session:
            await self._session.close()

    async def _generate_session(self) -> aiohttp.ClientSession:
        self._session = aiohttp.ClientSession()
        return self._session

    async def request(self, route: Route, **kwargs: Any) -> Any:
        if self._session is None:
            self._session = await self._generate_session()

        bucket = route.path
        lock = self._locks.get(bucket)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[bucket] = lock

        headers = kwargs.pop("headers", {})

        if self._token is not None:
            headers["Authorization"] = f"Bearer {self._token}"
        headers["User-Agent"] = self.user_agent

        if "json" in kwargs:
            headers["Content-Type"] = "application/json"
            kwargs["data"] = json.dumps(kwargs.pop("json"), separators=(",", ":"), ensure_ascii=True)
            LOGGER.debug("Current json body is: %s", str(kwargs["data"]))

        kwargs["headers"] = headers

        LOGGER.debug("Current request headers: %s", headers)
        LOGGER.debug("Current request url: %s", route.url)

        response: Optional[aiohttp.ClientResponse] = None
        await lock.acquire()
        with MaybeUnlock(lock) as maybe_lock:
            for tries in range(5):
                try:
                    async with self._session.request(route.verb, route.url, **kwargs) as response:
                        # Requests remaining before ratelimit
                        remaining = response.headers.get("x-ratelimit-remaining", None)
                        LOGGER.debug("remaining is: %s", remaining)
                        # Timestamp for when current ratelimit session(?) expires
                        retry = response.headers.get("x-ratelimit-retry-after", None)
                        LOGGER.debug("retry is: %s", retry)
                        if retry is not None:
                            retry = datetime.datetime.fromtimestamp(int(retry))
                        # The total ratelimit session hits
                        limit = response.headers.get("x-ratelimit-limit", None)
                        LOGGER.debug("limit is: %s", limit)

                        if remaining == "0" and response.status != 429:
                            assert retry is not None
                            delta = retry - datetime.datetime.now()
                            sleep = delta.total_seconds() + 1
                            LOGGER.warning("A ratelimit has been exhausted, sleeping for: %d", sleep)
                            maybe_lock.defer()
                            loop = asyncio.get_running_loop()
                            loop.call_later(sleep, lock.release)

                        data = await json_or_text(response)

                        if 300 > response.status >= 200:
                            return data

                        if response.status == 429:
                            assert retry is not None
                            delta = retry - datetime.datetime.now()
                            sleep = delta.total_seconds() + 1
                            LOGGER.warning("A ratelimit has been hit, sleeping for: %d", sleep)
                            await asyncio.sleep(sleep)
                            continue

                        if response.status in {500, 502, 503, 504}:
                            sleep_ = 1 + tries * 2
                            LOGGER.warning("Hit an API error, trying again in: %d", sleep_)
                            await asyncio.sleep(sleep_)
                            continue

                        assert isinstance(data, dict)
                        LOGGER.exception("Unhandled HTTP error occurred: %s -> %s", response.status, data)
                        raise APIException(
                            response=response,
                            status_code=response.status,
                        )
                except (aiohttp.ServerDisconnectedError, aiohttp.ServerTimeoutError) as error:
                    LOGGER.exception("Network error occurred: %s", error)
                    await asyncio.sleep(5)
                    continue

            if response is not None:
                if response.status >= 500:
                    raise APIException(response=response, status_code=response.status)

                raise APIException(response=response, status_code=response.status)

            raise RuntimeError("Unreachable code in HTTP handling.")

    def create_paste(
        self,
        *,
        file: Optional[File] = None,
        files: Optional[list[File]] = None,
        password: Optional[str],
        expires: Optional[datetime.datetime],
    ) -> Response[PasteResponse]:
        route = Route("PUT", "/paste")

        json_: dict[str, Any] = {}
        if file:
            json_["files"] = [file.to_dict()]
        elif files:
            json_["files"] = [f.to_dict() for f in files]

        if password:
            json_["password"] = password
        if expires:
            json_["expires"] = _clean_dt(expires)

        return self.request(route=route, json=json_)

    def delete_paste(self, *, paste_id: str) -> Response[None]:
        return self.delete_pastes(paste_ids=[paste_id])

    def delete_pastes(self, *, paste_ids: list[str]) -> Response[None]:
        route = Route("DELETE", "/paste")
        return self.request(route=route, json={"pastes": paste_ids})

    def get_paste(self, *, paste_id: str, password: Optional[str]) -> Response[PasteResponse]:
        route = Route("GET", "/paste/{paste_id}", paste_id=paste_id)

        if password:
            return self.request(route=route, params={"password": password})
        return self.request(route=route)

    def edit_paste(
        self,
        paste_id: str,
        *,
        new_content: str = MISSING,
        new_filename: str = MISSING,
        new_expires: datetime.datetime = MISSING,
    ) -> Response[EditPasteResponse]:
        route = Route("PATCH", "/paste/{paste_id}", paste_id=paste_id)

        json_: dict[str, Any] = {}

        if new_content is not MISSING:
            json_["new_content"] = new_content

        if new_filename is not MISSING:
            json_["new_filename"] = new_filename

        if new_expires is not MISSING:
            json_["new_expires"] = _clean_dt(new_expires)

        return self.request(route, json=json_)

    def get_my_pastes(self, *, limit: int) -> Response[list[PasteResponse]]:
        route = Route("GET", "/pastes/@me")

        return self.request(route, params={limit: limit})