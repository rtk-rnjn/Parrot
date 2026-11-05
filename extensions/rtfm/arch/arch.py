from __future__ import annotations

import asyncio
import datetime
import logging
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Literal, Self
from urllib.parse import quote

import aiohttp
import orjson
from lxml import etree
from lxml import html as lxml_html
from tenacity import AsyncRetrying, before_sleep_log, retry_if_exception_type, stop_after_attempt, wait_exponential

__all__ = (
    "AURPackage",
    "ArchScraper",
    "ArchScraperError",
    "NewsItem",
    "NotFoundError",
    "Package",
    "UpstreamError",
    "WikiPage",
    "WikiResult",
)

_log = logging.getLogger(__name__)

ARCH_URL = "https://archlinux.org"
AUR_URL = "https://aur.archlinux.org"
WIKI_URL = "https://wiki.archlinux.org"

DEFAULT_USER_AGENT = "arch-scraper/1.0 (discord bot; aiohttp)"
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR = 500
HTTP_CLIENT_ERROR = 400
AUR_INFO_CHUNK_SIZE = 100

type AurSearchBy = Literal[
    "name",
    "name-desc",
    "maintainer",
    "depends",
    "makedepends",
    "optdepends",
    "checkdepends",
]

_UTC = datetime.UTC
_DC_NS = "{http://purl.org/dc/elements/1.1/}"
_REPO_PRIORITY = {"core": 0, "extra": 1, "multilib": 2}


class ArchScraperError(Exception):
    """Base error for everything raised by this module."""


class NotFoundError(ArchScraperError):
    """The requested package or page does not exist."""


class UpstreamError(ArchScraperError):
    """The remote service failed, timed out, or returned garbage."""


class _Transient(Exception):
    """Internal marker for responses worth retrying (HTTP 429 and 5xx)."""


_RETRYABLE: tuple[type[BaseException], ...] = (
    aiohttp.ClientConnectionError,
    aiohttp.ClientPayloadError,
    TimeoutError,
    _Transient,
)


def _tuple(value: Any) -> tuple[str, ...]:
    return tuple(str(item) for item in value) if value else ()


def _dt_iso(value: Any) -> datetime.datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=_UTC)


def _dt_ts(value: Any) -> datetime.datetime | None:
    if value is None:
        return None
    try:
        return datetime.datetime.fromtimestamp(int(value), tz=_UTC)
    except TypeError, ValueError, OverflowError, OSError:
        return None


def _strip_html(text: str) -> str:
    """Turn an HTML fragment into plain text, falling back to the input if it cannot be parsed."""
    if not text or not text.strip():
        return ""
    try:
        node = lxml_html.fragment_fromstring(text, create_parent="div")
        return " ".join(node.text_content().split())
    except etree.ParserError, ValueError:
        return text.strip()


def _wiki_page_url(title: str) -> str:
    return f"{WIKI_URL}/title/{quote(title.replace(' ', '_'), safe='/:()_,')}"


@dataclass(slots=True, frozen=True)
class Package:
    """A package from the official repositories."""

    name: str
    base: str
    repo: str
    arch: str
    version: str
    description: str
    upstream_url: str | None
    licenses: tuple[str, ...]
    groups: tuple[str, ...]
    maintainers: tuple[str, ...]
    packager: str | None
    depends: tuple[str, ...]
    optdepends: tuple[str, ...]
    makedepends: tuple[str, ...]
    provides: tuple[str, ...]
    conflicts: tuple[str, ...]
    replaces: tuple[str, ...]
    compressed_size: int
    installed_size: int
    build_date: datetime.datetime | None
    last_update: datetime.datetime | None
    flagged_at: datetime.datetime | None

    @property
    def url(self) -> str:
        return f"{ARCH_URL}/packages/{self.repo}/{self.arch}/{self.name}/"

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Self:
        version = f"{data.get('pkgver', '')}-{data.get('pkgrel', '')}"
        if data.get("epoch"):
            version = f"{data['epoch']}:{version}"

        return cls(
            name=data["pkgname"],
            base=data.get("pkgbase") or data["pkgname"],
            repo=data.get("repo", ""),
            arch=data.get("arch", ""),
            version=version,
            description=data.get("pkgdesc") or "",
            upstream_url=data.get("url") or None,
            licenses=_tuple(data.get("licenses")),
            groups=_tuple(data.get("groups")),
            maintainers=_tuple(data.get("maintainers")),
            packager=data.get("packager") or None,
            depends=_tuple(data.get("depends")),
            optdepends=_tuple(data.get("optdepends")),
            makedepends=_tuple(data.get("makedepends")),
            provides=_tuple(data.get("provides")),
            conflicts=_tuple(data.get("conflicts")),
            replaces=_tuple(data.get("replaces")),
            compressed_size=int(data.get("compressed_size") or 0),
            installed_size=int(data.get("installed_size") or 0),
            build_date=_dt_iso(data.get("build_date")),
            last_update=_dt_iso(data.get("last_update")),
            flagged_at=_dt_iso(data.get("flag_date")),
        )


@dataclass(slots=True, frozen=True)
class AURPackage:
    """A package from the Arch User Repository."""

    name: str
    base: str
    version: str
    description: str
    upstream_url: str | None
    maintainer: str | None
    submitter: str | None
    votes: int
    popularity: float
    out_of_date: datetime.datetime | None
    first_submitted: datetime.datetime | None
    last_modified: datetime.datetime | None
    depends: tuple[str, ...]
    make_depends: tuple[str, ...]
    opt_depends: tuple[str, ...]
    check_depends: tuple[str, ...]
    licenses: tuple[str, ...]
    keywords: tuple[str, ...]
    provides: tuple[str, ...]
    conflicts: tuple[str, ...]

    @property
    def url(self) -> str:
        return f"{AUR_URL}/packages/{self.name}"

    @property
    def git_url(self) -> str:
        return f"{AUR_URL}/{self.base}.git"

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Self:
        return cls(
            name=data["Name"],
            base=data.get("PackageBase") or data["Name"],
            version=data.get("Version", ""),
            description=data.get("Description") or "",
            upstream_url=data.get("URL") or None,
            maintainer=data.get("Maintainer"),
            submitter=data.get("Submitter"),
            votes=int(data.get("NumVotes") or 0),
            popularity=float(data.get("Popularity") or 0.0),
            out_of_date=_dt_ts(data.get("OutOfDate")),
            first_submitted=_dt_ts(data.get("FirstSubmitted")),
            last_modified=_dt_ts(data.get("LastModified")),
            depends=_tuple(data.get("Depends")),
            make_depends=_tuple(data.get("MakeDepends")),
            opt_depends=_tuple(data.get("OptDepends")),
            check_depends=_tuple(data.get("CheckDepends")),
            licenses=_tuple(data.get("License")),
            keywords=_tuple(data.get("Keywords")),
            provides=_tuple(data.get("Provides")),
            conflicts=_tuple(data.get("Conflicts")),
        )


@dataclass(slots=True, frozen=True)
class WikiResult:
    title: str
    snippet: str
    url: str


@dataclass(slots=True, frozen=True)
class WikiPage:
    title: str
    summary: str
    url: str


@dataclass(slots=True, frozen=True)
class NewsItem:
    title: str
    link: str
    summary: str
    author: str | None
    published: datetime.datetime | None


class _TTLCache:
    def __init__(self, ttl: float, maxsize: int) -> None:
        self._ttl = ttl
        self._maxsize = maxsize
        self._data: dict[Any, tuple[float, Any]] = {}

    def get(self, key: Any) -> Any | None:
        item = self._data.get(key)
        if item is None:
            return None

        expires, value = item
        if expires < time.monotonic():
            del self._data[key]
            return None

        return value

    def set(self, key: Any, value: Any) -> None:
        if self._ttl <= 0:
            return

        if len(self._data) >= self._maxsize:
            self._data.pop(next(iter(self._data)))  # evict the oldest entry

        self._data[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        self._data.clear()


class ArchScraper:
    """Async client for Arch Linux's public endpoints: official repos, the AUR, the wiki and the news feed.

    Parameters
    ----------
    session
        Optional ``aiohttp.ClientSession``. When given it is used for every request and is never closed by
        this class. When omitted, a session is created lazily and closed by :meth:`close`.
    user_agent
        Sent on every request. It is set per request, so it also applies to an injected session.
    timeout
        Total timeout in seconds for each request.
    retries
        Maximum attempts per request for network errors, HTTP 429 and HTTP 5xx.
    max_concurrency
        Maximum number of simultaneous in-flight requests from this scraper.
    cache_ttl, cache_size
        In-memory response cache. ``cache_ttl=0`` disables it.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 15.0,
        retries: int = 3,
        max_concurrency: int = 5,
        cache_ttl: float = 300.0,
        cache_size: int = 256,
    ) -> None:
        self._session = session
        self._headers = {"User-Agent": user_agent}
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._retries = max(1, retries)
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._cache = _TTLCache(cache_ttl, cache_size)

    async def __aenter__(self) -> Self:
        return self

    def clear_cache(self) -> None:
        self._cache.clear()

    def _get_session(self) -> aiohttp.ClientSession:
        return self._session

    async def _fetch_once(
        self,
        session: aiohttp.ClientSession,
        url: str,
        params: Sequence[tuple[str, str]],
        kind: Literal["json", "bytes"],
    ) -> Any:
        async with (
            self._semaphore,
            session.get(url, params=list(params) or None, headers=self._headers, timeout=self._timeout) as response,
        ):
            if response.status == HTTP_NOT_FOUND:
                msg = f"404 Not Found: {url}"
                raise NotFoundError(msg)

            if response.status == HTTP_TOO_MANY_REQUESTS or response.status >= HTTP_SERVER_ERROR:
                msg = f"HTTP {response.status}"
                raise _Transient(msg)

            if response.status >= HTTP_CLIENT_ERROR:
                msg = f"HTTP {response.status} from {url}"
                raise UpstreamError(msg)

            if kind == "json":
                return await response.json(loads=orjson.loads, content_type=None)

            return await response.read()

    async def _get(
        self,
        url: str,
        params: Sequence[tuple[str, str]] = (),
        *,
        kind: Literal["json", "bytes"] = "json",
    ) -> Any:
        key = (url, tuple(params), kind)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        session = self._get_session()
        result: Any = None
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._retries),
                wait=wait_exponential(multiplier=0.5, max=5),
                retry=retry_if_exception_type(_RETRYABLE),
                before_sleep=before_sleep_log(_log, logging.WARNING),
                reraise=True,
            ):
                with attempt:
                    result = await self._fetch_once(session, url, params, kind)
        except ArchScraperError:
            raise
        except (*_RETRYABLE, aiohttp.ClientError, ValueError) as error:
            msg = f"Request to {url} failed: {error!r}"
            raise UpstreamError(msg) from error

        self._cache.set(key, result)
        return result

    async def search_packages(
        self,
        query: str,
        *,
        repos: Iterable[str] | None = None,
        arch: str | None = None,
        exact: bool = False,
        limit: int = 10,
    ) -> list[Package]:
        """Search the official repositories. ``exact=True`` matches the package name exactly."""
        params: list[tuple[str, str]] = [("name" if exact else "q", query)]
        params.extend(("repo", repo) for repo in repos or ())
        if arch:
            params.append(("arch", arch))

        data = await self._get(f"{ARCH_URL}/packages/search/json/", params)
        if not isinstance(data, dict) or data.get("valid") is False:
            msg = "Arch rejected the package search query."
            raise UpstreamError(msg)

        packages = [Package.from_json(result) for result in data.get("results", [])]
        needle = query.lower()
        packages.sort(key=lambda p: (p.name.lower() != needle, not p.name.lower().startswith(needle), len(p.name)))
        return packages[:limit]

    async def get_package(self, name: str, *, repo: str | None = None, arch: str | None = None) -> Package:
        """Exact-name lookup. Prefers core, then extra, then multilib, then everything else."""
        results = await self.search_packages(name, exact=True, repos=[repo] if repo else None, arch=arch, limit=50)
        if not results:
            msg = f"No official package named {name!r}."
            raise NotFoundError(msg)

        return min(results, key=lambda p: _REPO_PRIORITY.get(p.repo, 10))

    @staticmethod
    def _check_aur(data: Any) -> Any:
        if isinstance(data, dict) and data.get("type") == "error":
            msg = data.get("error") or "AUR returned an error."
            raise UpstreamError(msg)

        return data

    async def search_aur(self, query: str, *, by: AurSearchBy = "name-desc", limit: int = 10) -> list[AURPackage]:
        """Search the AUR. Exact name matches come first, then the most popular packages."""
        data = self._check_aur(
            await self._get(f"{AUR_URL}/rpc/", [("v", "5"), ("type", "search"), ("by", by), ("arg", query)]),
        )
        packages = [AURPackage.from_json(result) for result in data.get("results", [])]
        needle = query.lower()
        packages.sort(key=lambda p: (p.name.lower() != needle, -p.popularity, -p.votes))
        return packages[:limit]

    async def get_aur_packages(self, names: Iterable[str]) -> list[AURPackage]:
        """Fetch full info for many AUR packages, chunked and requested concurrently."""
        unique = list(dict.fromkeys(names))
        chunks = [unique[i : i + AUR_INFO_CHUNK_SIZE] for i in range(0, len(unique), AUR_INFO_CHUNK_SIZE)]

        async def fetch(chunk: list[str]) -> list[AURPackage]:
            params = [("v", "5"), ("type", "info"), *(("arg[]", name) for name in chunk)]
            data = self._check_aur(await self._get(f"{AUR_URL}/rpc/", params))
            return [AURPackage.from_json(result) for result in data.get("results", [])]

        groups = await asyncio.gather(*(fetch(chunk) for chunk in chunks))
        return [package for group in groups for package in group]

    async def get_aur_package(self, name: str) -> AURPackage:
        results = await self.get_aur_packages([name])
        if not results:
            msg = f"No AUR package named {name!r}."
            raise NotFoundError(msg)

        return results[0]

    async def suggest_aur(self, prefix: str) -> list[str]:
        """Package name suggestions for the given prefix."""
        data = await self._get(f"{AUR_URL}/rpc/", [("v", "5"), ("type", "suggest"), ("arg", prefix)])
        self._check_aur(data)
        return [str(name) for name in data] if isinstance(data, list) else []

    async def search_wiki(self, query: str, *, limit: int = 5) -> list[WikiResult]:
        data = await self._get(
            f"{WIKI_URL}/api.php",
            [
                ("action", "query"),
                ("list", "search"),
                ("srsearch", query),
                ("srlimit", str(limit)),
                ("srprop", "snippet"),
                ("format", "json"),
                ("formatversion", "2"),
            ],
        )
        hits = (data.get("query") or {}).get("search") or []
        return [WikiResult(title=hit["title"], snippet=_strip_html(hit.get("snippet", "")), url=_wiki_page_url(hit["title"])) for hit in hits]

    async def get_wiki_summary(self, title: str) -> WikiPage:
        """The intro section of a wiki page as plain text. Redirects are followed."""
        data = await self._get(
            f"{WIKI_URL}/api.php",
            [
                ("action", "query"),
                ("prop", "extracts"),
                ("exintro", "1"),
                ("explaintext", "1"),
                ("redirects", "1"),
                ("titles", title),
                ("format", "json"),
                ("formatversion", "2"),
            ],
        )
        pages = (data.get("query") or {}).get("pages") or []
        if not pages or pages[0].get("missing"):
            msg = f"No wiki page titled {title!r}."
            raise NotFoundError(msg)

        page = pages[0]
        return WikiPage(title=page["title"], summary=(page.get("extract") or "").strip(), url=_wiki_page_url(page["title"]))

    async def get_news(self, limit: int = 5) -> list[NewsItem]:
        raw: bytes = await self._get(f"{ARCH_URL}/feeds/news/", kind="bytes")
        parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
        try:
            root = etree.fromstring(raw, parser=parser)  # entity resolution and network access are disabled
        except etree.XMLSyntaxError as error:
            msg = "Arch news feed was not valid XML."
            raise UpstreamError(msg) from error

        items: list[NewsItem] = []
        for node in root.iterfind("./channel/item"):
            published = None
            raw_date = node.findtext("pubDate")
            if raw_date:
                try:
                    published = parsedate_to_datetime(raw_date)
                except TypeError, ValueError:
                    published = None

            items.append(
                NewsItem(
                    title=(node.findtext("title") or "").strip(),
                    link=(node.findtext("link") or "").strip(),
                    summary=_strip_html(node.findtext("description") or ""),
                    author=node.findtext(f"{_DC_NS}creator"),
                    published=published,
                ),
            )
            if len(items) >= limit:
                break

        return items
