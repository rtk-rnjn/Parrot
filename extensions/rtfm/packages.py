from __future__ import annotations

import abc
import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parseaddr
from functools import partial
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Literal
from urllib.parse import quote

import aiohttp
import arrow
import discord
from bs4 import BeautifulSoup
from discord.ext import commands
from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import InvalidVersion, Version

from core.utils import BaseLayoutView, NoticeLayout, truncate

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from core import Bot

__all__ = ("Packages",)

USER_AGENT = "Parrot Discord bot (https://github.com/rtk-rnjn/Parrot)"
TIMEOUT = aiohttp.ClientTimeout(total=15)
MAX_RESPONSE = 8 * 1024 * 1024
MAX_PACKUMENT = 30 * 1024 * 1024  # the full npm document of a package can be huge

DOT = " \N{MIDDLE DOT} "
VERSIONS_PER_PAGE = 12
MAX_VERSIONS = 120
SEARCH_LIMIT = 8
DEPENDENCY_BUDGET = 3000  # characters of dependency names across the whole message (the message limit is 4000)
GROUP_BUDGET = 1100
MAX_GROUPS = 8

EXTRA_MARKER = re.compile(r"""extra\s*==\s*["']([^"']+)["']""")
VERSION_PATTERN = re.compile(r"[0-9A-Za-z.+_~^!*-]{1,64}")
REPO_HOSTS = ("github.com", "gitlab.com", "bitbucket.org", "codeberg.org", "sr.ht")


@dataclass(frozen=True, slots=True, eq=False)
class Ecosystem:
    key: str
    label: str
    colour: discord.Colour
    icon: str
    install: str
    requires_label: str
    name_pattern: re.Pattern[str]
    aliases: tuple[str, ...]
    page: str

    def page_url(self, name: str) -> str:
        return self.page.format(name=quote(name, safe="@/"))


PYPI = Ecosystem(
    key="pypi",
    label="PyPI",
    colour=discord.Colour.teal(),
    icon="https://i.imgur.com/syDydkb.png",
    install="pip install {name}",
    requires_label="Python",
    name_pattern=re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,98}[A-Za-z0-9])?"),
    aliases=("pypi", "pip", "py", "python"),
    page="https://pypi.org/project/{name}/",
)
NPM = Ecosystem(
    key="npm",
    label="npm",
    colour=discord.Colour(0xCC3534),
    icon="https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Npm-logo.svg/800px-Npm-logo.svg.png",
    install="npm install {name}",
    requires_label="Node.js",
    name_pattern=re.compile(r"(?:@[a-z0-9][a-z0-9._~-]*/)?[a-z0-9][a-z0-9._~-]*", re.IGNORECASE),
    aliases=("npm", "node", "nodejs", "js", "javascript"),
    page="https://www.npmjs.com/package/{name}",
)
CRATES = Ecosystem(
    key="crates",
    label="crates.io",
    colour=discord.Colour(0xE03D29),
    icon="https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/Rust_programming_language_black_logo.svg/2048px-Rust_programming_language_black_logo.svg.png",
    install="cargo add {name}",
    requires_label="Rust",
    name_pattern=re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}"),
    aliases=("crates", "crate", "cargo", "rust"),
    page="https://crates.io/crates/{name}",
)
ECOSYSTEMS = (PYPI, NPM, CRATES)


class EcosystemConverter(commands.Converter[Ecosystem]):
    async def convert(self, ctx: commands.Context[Bot], argument: str) -> Ecosystem:
        wanted = argument.strip().casefold()
        for ecosystem in ECOSYSTEMS:
            if wanted == ecosystem.label.casefold() or wanted in ecosystem.aliases:
                return ecosystem
        msg = "The ecosystem should be `pypi`, `npm` or `crates`."
        raise commands.BadArgument(msg)


class RegistryError(Exception):
    """A problem that should be shown to the user as-is."""


@dataclass(slots=True)
class PackageInfo:
    ecosystem: Ecosystem
    name: str
    version: str
    url: str
    summary: str | None = None
    license: str | None = None
    author: str | None = None
    homepage: str | None = None
    repository: str | None = None
    documentation: str | None = None
    released: str | None = None
    first_release: str | None = None
    release_count: int | None = None
    dependencies: int | None = None
    downloads: int | None = None
    downloads_label: str = ""
    size: int | None = None
    requires: str | None = None
    keywords: list[str] = field(default_factory=list)
    deprecated: str | None = None
    yanked: bool = False
    warning: str | None = None
    facts: list[tuple[str, str]] = field(default_factory=list)
    extra_links: list[tuple[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class VersionEntry:
    version: str
    released: str | None = None
    prerelease: bool = False
    yanked: bool = False
    deprecated: bool = False
    tags: list[str] = field(default_factory=list)
    note: str | None = None


@dataclass(slots=True)
class VersionList:
    name: str
    latest: str | None
    entries: list[VersionEntry]
    total: int
    url: str


@dataclass(slots=True)
class DependencyList:
    name: str
    version: str
    groups: dict[str, list[str]]
    url: str
    requires: str | None = None


@dataclass(slots=True)
class SearchHit:
    name: str
    version: str | None
    description: str | None
    url: str
    updated: str | None = None
    detail: str | None = None


@dataclass(slots=True)
class SearchResult:
    hits: list[SearchHit]
    total: int | None = None
    note: str | None = None


def safe(text: str | None, limit: int = 200) -> str:
    flat = " ".join((text or "").split())
    return truncate(discord.utils.escape_markdown(discord.utils.escape_mentions(flat)), limit)


def code(text: str, limit: int = 60) -> str:
    return f"`{truncate(text.replace('`', chr(39)), limit)}`"


def compact(number: int) -> str:
    for threshold, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "k")):
        if number >= threshold:
            return f"{number / threshold:.1f}".rstrip("0").rstrip(".") + suffix
    return str(number)


def file_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def parse_time(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        return arrow.get(iso).datetime
    except ValueError, TypeError:
        return None


def when(iso: str | None, style: Literal["f", "F", "d", "D", "t", "T", "s", "S", "R"] = "R") -> str | None:
    moment = parse_time(iso)
    return discord.utils.format_dt(moment, style) if moment else None


def dated(iso: str | None) -> str | None:
    return f"{when(iso, 'D')} ({when(iso)})" if parse_time(iso) else None


def day(iso: str | None) -> str | None:
    moment = parse_time(iso)
    return moment.strftime("%Y-%m-%d") if moment else None


def valid_url(url: str | None) -> bool:
    return bool(url) and url.startswith(("http://", "https://")) and len(url) <= 512


def pick_url(urls: dict[str, str], keys: Sequence[str]) -> str | None:
    lowered = {key.casefold(): value for key, value in urls.items()}
    return next((lowered[key] for key in keys if lowered.get(key)), None)


def normalize_repo(value: Any) -> str | None:
    url = value.get("url") if isinstance(value, dict) else value
    if not isinstance(url, str) or not url.strip():
        return None
    url = url.strip().removeprefix("git+")
    if url.startswith("git://"):
        url = "https://" + url.removeprefix("git://")
    elif url.startswith("ssh://git@"):
        url = "https://" + url.removeprefix("ssh://git@")
    elif url.startswith("git@"):
        url = "https://" + url.removeprefix("git@").replace(":", "/", 1)
    elif url.startswith("github:"):
        url = "https://github.com/" + url.removeprefix("github:")
    elif re.fullmatch(r"[\w.-]+/[\w.-]+", url):
        url = "https://github.com/" + url
    return url.removesuffix(".git") if url.startswith("http") else None


def person(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("name") or None
    if isinstance(value, str):
        return re.split(r"\s*[<(]", value, maxsplit=1)[0].strip() or None
    return None


def prerelease(version: str) -> bool:
    try:
        return Version(version).is_prerelease
    except InvalidVersion:
        return "-" in version


def version_key(version: str) -> tuple[int, Version]:
    try:
        return 1, Version(version)
    except InvalidVersion:
        return 0, Version("0")


def text(content: str) -> discord.ui.TextDisplay:
    return discord.ui.TextDisplay(content)


def facts(*pairs: tuple[str, str | None]) -> discord.ui.TextDisplay | None:
    lines = [f"**{label}**: {value}" for label, value in pairs if value]
    return text("\n".join(lines)) if lines else None


def collect(*items: discord.ui.Item | None) -> list[discord.ui.Item]:
    return [item for item in items if item is not None]


def header(title: str, subtitle: str | None = None, *extra: str, thumbnail: str | None = None) -> discord.ui.Item:
    parts = [text(f"## {title}" + (f"\n-# {subtitle}" if subtitle else ""))]
    parts.extend(text(line) for line in extra if line)
    if thumbnail:
        return discord.ui.Section(*parts, accessory=discord.ui.Thumbnail(thumbnail))
    return text("\n".join(part.content for part in parts))


def pack(entries: Sequence[str], limit: int) -> str:
    """Inline-code chips that fit in ``limit`` characters, followed by how many were left out."""
    shown: list[str] = []
    used = 0
    for entry in entries:
        piece = f"`{entry.replace('`', chr(39))}`"
        if used + len(piece) + 1 > limit:
            break
        shown.append(piece)
        used += len(piece) + 1
    left = len(entries) - len(shown)
    return " ".join(shown) + (f" *+{left} more*" if left else "")


class Fetcher:
    """Small wrapper that adds a User-Agent, limits response size and turns failures into :class:`RegistryError`."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    async def raw(
        self,
        url: str,
        *,
        source: str,
        missing: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        limit: int = MAX_RESPONSE,
    ) -> bytes:
        merged = {"User-Agent": USER_AGENT, **(headers or {})}
        try:
            async with self.session.get(url, params=params, headers=merged, timeout=TIMEOUT) as response:
                status = response.status
                if status == 404:
                    raise RegistryError(missing)
                if status == 429:
                    retry = response.headers.get("Retry-After")
                    msg = f"{source} is rate limiting requests right now." + (f" Try again in {retry} seconds." if retry and retry.isdigit() else "")
                    raise RegistryError(msg)
                if status >= 400:
                    msg = f"{source} returned an error ({status})."
                    raise RegistryError(msg)

                chunks: list[bytes] = []
                size = 0
                async for chunk in response.content.iter_chunked(64 * 1024):
                    size += len(chunk)
                    if size > limit:
                        msg = f"The data {source} has for this package is too large to process."
                        raise RegistryError(msg)
                    chunks.append(chunk)
        except (TimeoutError, aiohttp.ClientError) as error:
            msg = f"Could not reach {source} right now. Try again in a moment."
            raise RegistryError(msg) from error
        return b"".join(chunks)

    async def json(self, url: str, *, source: str, missing: str, **kwargs: Any) -> Any:
        raw = await self.raw(url, source=source, missing=missing, **kwargs)
        try:
            return await asyncio.to_thread(json.loads, raw)
        except ValueError as error:
            msg = f"{source} sent a response that could not be read."
            raise RegistryError(msg) from error

    async def text(self, url: str, *, source: str, missing: str, **kwargs: Any) -> str:
        return (await self.raw(url, source=source, missing=missing, **kwargs)).decode("utf-8", "replace")


class Registry(abc.ABC):
    ecosystem: ClassVar[Ecosystem]

    def __init__(self, fetch: Fetcher) -> None:
        self.fetch = fetch

    def validate(self, name: str) -> str:
        cleaned = name.strip()
        if not self.ecosystem.name_pattern.fullmatch(cleaned):
            msg = f"`{truncate(cleaned.replace('`', ''), 50)}` is not a valid {self.ecosystem.label} package name."
            raise RegistryError(msg)
        return cleaned

    @staticmethod
    def validate_version(version: str | None) -> str | None:
        if version is None:
            return None
        cleaned = version.strip().removeprefix("v") if version.strip().startswith("v") else version.strip()
        if not VERSION_PATTERN.fullmatch(cleaned):
            msg = f"`{truncate(version.replace('`', ''), 30)}` is not a valid version."
            raise RegistryError(msg)
        return cleaned

    @staticmethod
    async def attempt(awaitable: Awaitable[Any]) -> Any | None:
        """Await something that is only nice to have; a failure yields ``None``."""
        try:
            return await awaitable
        except RegistryError:
            return None

    @abc.abstractmethod
    async def info(self, name: str) -> PackageInfo: ...

    @abc.abstractmethod
    async def versions(self, name: str) -> VersionList: ...

    @abc.abstractmethod
    async def dependencies(self, name: str, version: str | None) -> DependencyList: ...

    @abc.abstractmethod
    async def search(self, query: str) -> SearchResult: ...


class PyPIRegistry(Registry):
    ecosystem = PYPI

    async def project(self, name: str, version: str | None = None) -> dict[str, Any]:
        quoted = quote(name, safe="")
        if version:
            url = f"https://pypi.org/pypi/{quoted}/{quote(version, safe='')}/json"
            missing = f"Version `{version}` of `{name}` was not found on PyPI."
        else:
            url = f"https://pypi.org/pypi/{quoted}/json"
            missing = f"`{name}` was not found on PyPI."
        return await self.fetch.json(url, source="PyPI", missing=missing)

    @staticmethod
    def license_of(info: dict[str, Any]) -> str | None:
        if expression := info.get("license_expression"):
            return expression
        for classifier in info.get("classifiers") or []:
            if classifier.startswith("License :: "):
                return classifier.rsplit(" :: ", 1)[-1]
        licence = (info.get("license") or "").strip()
        return licence if licence and len(licence) <= 40 and "\n" not in licence else None

    async def info(self, name: str) -> PackageInfo:
        data, stats = await asyncio.gather(
            self.project(name),
            self.attempt(
                self.fetch.json(f"https://pypistats.org/api/packages/{quote(name.lower(), safe='')}/recent", source="PyPI Stats", missing="")
            ),
        )
        info = data["info"]
        releases = {version: files for version, files in (data.get("releases") or {}).items() if files}
        uploads = [file["upload_time_iso_8601"] for files in releases.values() for file in files if file.get("upload_time_iso_8601")]

        latest_files = data.get("urls") or []
        latest_times = [file["upload_time_iso_8601"] for file in latest_files if file.get("upload_time_iso_8601")]
        artifact = next((file for file in latest_files if file.get("packagetype") == "bdist_wheel"), latest_files[0] if latest_files else None)

        requires = [item for item in info.get("requires_dist") or [] if not EXTRA_MARKER.search(item)]
        urls = info.get("project_urls") or {}
        homepage = pick_url(urls, ("homepage", "home", "home page")) or info.get("home_page") or None
        repository = pick_url(urls, ("source", "source code", "repository", "code", "github", "git", "gitlab"))
        if repository is None and homepage and any(host in homepage for host in REPO_HOSTS):
            repository = homepage

        keywords_raw = (info.get("keywords") or "").strip()
        keywords = [word for word in re.split(r"[,\s]+" if "," not in keywords_raw else r"\s*,\s*", keywords_raw) if word]

        email = info.get("author_email") or ""
        vulnerabilities = data.get("vulnerabilities") or []
        weekly = ((stats or {}).get("data") or {}).get("last_week")

        return PackageInfo(
            ecosystem=PYPI,
            name=info["name"],
            version=info["version"],
            url=PYPI.page_url(info["name"]),
            summary=info.get("summary"),
            license=self.license_of(info),
            author=info.get("author") or parseaddr(email)[0] or None,
            homepage=homepage,
            repository=repository,
            documentation=pick_url(urls, ("documentation", "docs", "documentation url")),
            released=min(latest_times, default=None),
            first_release=min(uploads, default=None),
            release_count=len(releases) or None,
            dependencies=len(requires),
            downloads=weekly,
            downloads_label="last week",
            size=artifact.get("size") if artifact else None,
            requires=info.get("requires_python") or None,
            keywords=keywords[:10],
            yanked=bool(info.get("yanked")),
            warning=(
                f"{len(vulnerabilities)} known vulnerabilit{'y' if len(vulnerabilities) == 1 else 'ies'} reported for this version."
                if vulnerabilities
                else None
            ),
            facts=[("Author email", email)] if "@" in email else [],
        )

    async def versions(self, name: str) -> VersionList:
        data = await self.project(name)
        entries: list[VersionEntry] = []
        for version, files in (data.get("releases") or {}).items():
            if not files:  # every file of this release was deleted, so it cannot be installed
                continue
            times = [file["upload_time_iso_8601"] for file in files if file.get("upload_time_iso_8601")]
            entries.append(VersionEntry(version, min(times, default=None), prerelease(version), yanked=all(file.get("yanked") for file in files)))
        if not entries:
            entries = await self.simple_versions(name)

        entries.sort(key=lambda entry: version_key(entry.version), reverse=True)
        canonical = data["info"]["name"]
        return VersionList(canonical, data["info"]["version"], entries, len(entries), f"{PYPI.page_url(canonical)}#history")

    async def simple_versions(self, name: str) -> list[VersionEntry]:
        """Fallback for when the JSON API stops including ``releases``: the PEP 691 simple index lists versions without dates."""
        canonical = re.sub(r"[-_.]+", "-", name).lower()
        data = await self.fetch.json(
            f"https://pypi.org/simple/{quote(canonical, safe='')}/",
            headers={"Accept": "application/vnd.pypi.simple.v1+json"},
            source="PyPI",
            missing=f"`{name}` was not found on PyPI.",
        )
        return [VersionEntry(version, None, prerelease(version)) for version in data.get("versions") or []]

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        data = await self.project(name, version)
        info = data["info"]

        groups: dict[str, list[str]] = {}
        for raw in info.get("requires_dist") or []:
            try:
                requirement = Requirement(raw)
            except InvalidRequirement:
                groups.setdefault("Other", []).append(truncate(raw, 60))
                continue

            marker = str(requirement.marker) if requirement.marker else ""
            label = f"{requirement.name}{requirement.specifier}"
            if extras := EXTRA_MARKER.findall(marker):
                for extra in dict.fromkeys(extras):
                    groups.setdefault(f"Extra: {extra}", []).append(label)
            else:
                groups.setdefault("Required", []).append(label + (f" ; {truncate(marker, 40)}" if marker else ""))

        def order(item: tuple[str, list[str]]) -> tuple[int, str]:
            return (0 if item[0] == "Required" else 2 if item[0] == "Other" else 1, item[0])

        ordered = {group: sorted(entries, key=str.lower) for group, entries in sorted(groups.items(), key=order)}
        return DependencyList(info["name"], info["version"], ordered, PYPI.page_url(info["name"]), info.get("requires_python") or None)

    async def search(self, query: str) -> SearchResult:
        """PyPI has no JSON search API, so this reads the HTML search page and degrades to an exact match if that is blocked."""
        hits: list[SearchHit] = []
        try:
            html = await self.fetch.text(
                "https://pypi.org/search/", params={"q": query}, headers={"Accept": "text/html"}, source="PyPI", missing="PyPI search is unavailable."
            )
            hits = await asyncio.to_thread(self.parse_search, html)
        except RegistryError:
            hits = []
        if hits:
            return SearchResult(hits)

        if PYPI.name_pattern.fullmatch(query.strip()):
            try:
                data = await self.project(query.strip())
            except RegistryError:
                data = None
            if data:
                info = data["info"]
                hit = SearchHit(info["name"], info["version"], info.get("summary"), PYPI.page_url(info["name"]))
                return SearchResult([hit], note="PyPI's full-text search is unavailable right now, so only an exact name match is shown.")
        msg = f"No packages matched {code(query)} on PyPI, or PyPI search is unavailable right now."
        raise RegistryError(msg)

    @staticmethod
    def parse_search(html: str) -> list[SearchHit]:
        soup = BeautifulSoup(html, "html.parser")
        hits: list[SearchHit] = []
        for link in soup.select("a.package-snippet")[:SEARCH_LIMIT]:
            name = link.select_one(".package-snippet__name")
            if name is None:
                continue
            version = link.select_one(".package-snippet__version")
            description = link.select_one(".package-snippet__description")
            created = link.select_one(".package-snippet__created time")
            package = name.get_text(strip=True)
            hits.append(
                SearchHit(
                    package,
                    version.get_text(strip=True) if version else None,
                    description.get_text(strip=True) if description else None,
                    PYPI.page_url(package),
                    created.get("datetime") if created else None,  # type: ignore[arg-type]
                )
            )
        return hits


class NpmRegistry(Registry):
    ecosystem = NPM
    base = "https://registry.npmjs.org"

    @staticmethod
    def encode(name: str) -> str:
        return quote(name, safe="@")  # the slash of a scoped package must be escaped

    async def info(self, name: str) -> PackageInfo:
        manifest, weekly = await asyncio.gather(
            self.fetch.json(f"{self.base}/{self.encode(name)}/latest", source="npm", missing=f"`{name}` was not found on npm."),
            self.attempt(self.fetch.json(f"https://api.npmjs.org/downloads/point/last-week/{quote(name, safe='@/')}", source="npm", missing="")),
        )
        dependencies = manifest.get("dependencies") or {}
        maintainers = [person(entry) or "" for entry in manifest.get("maintainers") or []]
        maintainers = [entry for entry in maintainers if entry]

        return PackageInfo(
            ecosystem=NPM,
            name=manifest["name"],
            version=manifest["version"],
            url=NPM.page_url(manifest["name"]),
            summary=manifest.get("description"),
            license=self.license_of(manifest.get("license")),
            author=person(manifest.get("author")),
            homepage=manifest.get("homepage"),
            repository=normalize_repo(manifest.get("repository")),
            dependencies=len(dependencies),
            downloads=(weekly or {}).get("downloads"),
            downloads_label="last week",
            size=(manifest.get("dist") or {}).get("unpackedSize"),
            requires=(manifest.get("engines") or {}).get("node") if isinstance(manifest.get("engines"), dict) else None,
            keywords=[word for word in manifest.get("keywords") or [] if isinstance(word, str)][:10],
            deprecated=manifest.get("deprecated") or None,
            facts=[("Maintainers", ", ".join(maintainers[:5]) + (f" +{len(maintainers) - 5}" if len(maintainers) > 5 else ""))]
            if maintainers
            else [],
        )

    @classmethod
    def license_of(cls, value: Any) -> str | None:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return value.get("type")
        if isinstance(value, list):
            return ", ".join(filter(None, (cls.license_of(item) for item in value))) or None
        return None

    async def versions(self, name: str) -> VersionList:
        data = await self.fetch.json(f"{self.base}/{self.encode(name)}", source="npm", missing=f"`{name}` was not found on npm.", limit=MAX_PACKUMENT)
        published = data.get("time") or {}
        tags = data.get("dist-tags") or {}
        tagged: dict[str, list[str]] = {}
        for tag, version in tags.items():
            tagged.setdefault(version, []).append(tag)

        entries = [
            VersionEntry(
                version,
                published.get(version),
                prerelease(version) if "-" in version else False,
                deprecated=bool(manifest.get("deprecated")),
                tags=tagged.get(version, []),
            )
            for version, manifest in (data.get("versions") or {}).items()
        ]
        entries.sort(key=lambda entry: entry.released or "", reverse=True)
        return VersionList(data.get("name", name), tags.get("latest"), entries, len(entries), NPM.page_url(data.get("name", name)))

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        manifest = await self.fetch.json(
            f"{self.base}/{self.encode(name)}/{quote(version or 'latest', safe='')}",
            source="npm",
            missing=f"Version `{version}` of `{name}` was not found on npm." if version else f"`{name}` was not found on npm.",
        )
        sections = (
            ("Dependencies", "dependencies"),
            ("Peer dependencies", "peerDependencies"),
            ("Optional dependencies", "optionalDependencies"),
            ("Dev dependencies", "devDependencies"),
        )
        groups: dict[str, list[str]] = {}
        for title, key in sections:
            entries = manifest.get(key) or {}
            if isinstance(entries, dict) and entries:
                groups[title] = sorted((f"{package}@{requirement}" for package, requirement in entries.items()), key=str.lower)

        engines = manifest.get("engines")
        node = engines.get("node") if isinstance(engines, dict) else None
        return DependencyList(manifest["name"], manifest["version"], groups, NPM.page_url(manifest["name"]), node)

    async def search(self, query: str) -> SearchResult:
        data = await self.fetch.json(
            f"{self.base}/-/v1/search", params={"text": query, "size": SEARCH_LIMIT}, source="npm", missing="npm search is unavailable."
        )
        hits = []
        for entry in data.get("objects") or []:
            package = entry["package"]
            publisher = (package.get("publisher") or {}).get("username")
            hits.append(
                SearchHit(
                    package["name"],
                    package.get("version"),
                    package.get("description"),
                    NPM.page_url(package["name"]),
                    package.get("date"),
                    f"by {publisher}" if publisher else None,
                )
            )
        if not hits:
            msg = f"No packages matched {code(query)} on npm."
            raise RegistryError(msg)
        return SearchResult(hits, data.get("total"))


class CratesRegistry(Registry):
    ecosystem = CRATES
    base = "https://crates.io/api/v1"

    async def crate(self, name: str) -> dict[str, Any]:
        return await self.fetch.json(f"{self.base}/crates/{quote(name, safe='')}", source="crates.io", missing=f"The crate `{name}` was not found.")

    @staticmethod
    def default_version(data: dict[str, Any]) -> str | None:
        crate = data["crate"]
        return crate.get("max_stable_version") or crate.get("max_version") or crate.get("newest_version")

    async def info(self, name: str) -> PackageInfo:
        data = await self.crate(name)
        crate = data["crate"]
        versions = data.get("versions") or []
        number = self.default_version(data)
        latest = next((entry for entry in versions if entry["num"] == number), versions[0] if versions else {})

        dependencies = None
        if number:
            payload = await self.attempt(
                self.fetch.json(
                    f"{self.base}/crates/{quote(crate['name'], safe='')}/{quote(number, safe='')}/dependencies", source="crates.io", missing=""
                )
            )
            if payload:
                dependencies = sum(1 for dep in payload.get("dependencies") or [] if dep["kind"] == "normal" and not dep["optional"])

        publisher = latest.get("published_by") or {}
        keywords = [
            entry.get("keyword", entry.get("id")) if isinstance(entry, dict) else entry
            for entry in data.get("keywords") or crate.get("keywords") or []
        ]
        categories = [entry.get("category") for entry in data.get("categories") or [] if isinstance(entry, dict)]
        docs = crate.get("documentation") or f"https://docs.rs/{crate['name']}"

        facts_list = [("All-time downloads", f"{crate['downloads']:,}")] if crate.get("downloads") else []
        if publisher:
            facts_list.append(("Published by", publisher.get("name") or publisher.get("login") or "unknown"))
        if categories:
            facts_list.append(("Categories", ", ".join(filter(None, categories[:4]))))

        return PackageInfo(
            ecosystem=CRATES,
            name=crate["name"],
            version=number or "unknown",
            url=CRATES.page_url(crate["name"]),
            summary=crate.get("description"),
            license=latest.get("license"),
            homepage=crate.get("homepage"),
            repository=crate.get("repository"),
            documentation=docs,
            released=latest.get("created_at"),
            first_release=min((entry["created_at"] for entry in versions if entry.get("created_at")), default=None),
            release_count=len(versions) or None,
            dependencies=dependencies,
            downloads=crate.get("recent_downloads"),
            downloads_label="last 90 days",
            size=latest.get("crate_size"),
            requires=latest.get("rust_version"),
            keywords=[word for word in keywords if word][:10],
            yanked=bool(latest.get("yanked")),
            facts=facts_list,
        )

    async def versions(self, name: str) -> VersionList:
        data = await self.crate(name)
        crate = data["crate"]
        entries = [
            VersionEntry(
                entry["num"],
                entry.get("created_at"),
                "-" in entry["num"],
                yanked=bool(entry.get("yanked")),
                note=f"{compact(entry['downloads'])} downloads" if entry.get("downloads") else None,
            )
            for entry in data.get("versions") or []
        ]
        entries.sort(key=lambda entry: entry.released or "", reverse=True)
        return VersionList(crate["name"], self.default_version(data), entries, len(entries), f"{CRATES.page_url(crate['name'])}/versions")

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        data = await self.crate(name)
        crate = data["crate"]
        number = version or self.default_version(data)
        if not number:
            msg = f"`{crate['name']}` has no published versions."
            raise RegistryError(msg)

        payload = await self.fetch.json(
            f"{self.base}/crates/{quote(crate['name'], safe='')}/{quote(number, safe='')}/dependencies",
            source="crates.io",
            missing=f"Version `{number}` of `{crate['name']}` was not found.",
        )
        groups: dict[str, list[str]] = {}
        for dep in payload.get("dependencies") or []:
            if dep["kind"] == "dev":
                title = "Dev dependencies"
            elif dep["kind"] == "build":
                title = "Build dependencies"
            elif dep["optional"]:
                title = "Optional dependencies"
            else:
                title = "Dependencies"
            groups.setdefault(title, []).append(f"{dep['crate_id']}@{dep['req']}")

        order = ("Dependencies", "Optional dependencies", "Build dependencies", "Dev dependencies")
        ordered = {title: sorted(groups[title], key=str.lower) for title in order if title in groups}

        match = next((entry for entry in data.get("versions") or [] if entry["num"] == number), {})
        return DependencyList(crate["name"], number, ordered, CRATES.page_url(crate["name"]), match.get("rust_version"))

    async def search(self, query: str) -> SearchResult:
        data = await self.fetch.json(
            f"{self.base}/crates",
            params={"q": query, "per_page": SEARCH_LIMIT, "sort": "relevance"},
            source="crates.io",
            missing="Search is unavailable.",
        )
        hits = [
            SearchHit(
                entry["name"],
                entry.get("max_stable_version") or entry.get("max_version"),
                entry.get("description"),
                CRATES.page_url(entry["name"]),
                entry.get("updated_at"),
                f"{compact(entry['downloads'])} downloads" if entry.get("downloads") else None,
            )
            for entry in data.get("crates") or []
        ]
        if not hits:
            msg = f"No crates matched {code(query)}."
            raise RegistryError(msg)
        return SearchResult(hits, (data.get("meta") or {}).get("total"))


@dataclass(slots=True)
class Page:
    body: Callable[[], list[discord.ui.Item]]
    url: str | None = None
    label: str = "Open"
    colour: discord.Colour = field(default_factory=discord.Colour.blurple)
    links: list[tuple[str, str]] = field(default_factory=list)


class PackageView(BaseLayoutView):
    """One container with the page content, Previous/Next buttons when there are several pages, and link buttons."""

    def __init__(self, author: discord.User | discord.Member, pages: Sequence[Page], *, timeout: float = 180) -> None:
        super().__init__(author, timeout=timeout)
        self.pages = list(pages)
        self.index = 0
        self.container = discord.ui.Container(accent_colour=self.pages[0].colour)
        self.add_item(self.container)
        self.render()

    def render(self) -> None:
        page = self.pages[self.index]
        self.container.clear_items()
        self.container.accent_colour = page.colour
        for item in page.body():
            self.container.add_item(item)

        rows: list[discord.ui.ActionRow] = []
        if len(self.pages) > 1:
            rows.append(
                discord.ui.ActionRow(
                    self._nav_button("Previous", -1, "\N{BLACK LEFT-POINTING TRIANGLE}", disabled=self.index == 0),
                    discord.ui.Button(label=f"{self.index + 1} / {len(self.pages)}", disabled=True),
                    self._nav_button("Next", 1, "\N{BLACK RIGHT-POINTING TRIANGLE}", disabled=self.index >= len(self.pages) - 1),
                )
            )

        links = ([(page.label, page.url)] if page.url else []) + page.links
        buttons = [discord.ui.Button(label=label[:80], url=url) for label, url in links if valid_url(url)][:5]
        if buttons:
            rows.append(discord.ui.ActionRow(*buttons))

        if rows:
            self.container.add_item(discord.ui.Separator())
            for row in rows:
                self.container.add_item(row)

    def _nav_button(self, label: str, step: int, emoji: str, *, disabled: bool) -> discord.ui.Button:
        button = discord.ui.Button(label=label, emoji=emoji, disabled=disabled)

        async def callback(interaction: discord.Interaction) -> None:
            self.index = max(0, min(len(self.pages) - 1, self.index + step))
            self.render()
            await interaction.response.edit_message(view=self)

        button.callback = callback
        return button


def info_items(info: PackageInfo) -> list[discord.ui.Item]:
    eco = info.ecosystem
    badges = []
    if info.deprecated:
        badges.append("\N{WARNING SIGN}\N{VARIATION SELECTOR-16} Deprecated")
    if info.yanked:
        badges.append("\N{NO ENTRY SIGN} Yanked")

    description = safe(info.summary, 400) if info.summary else "*No description provided.*"
    alert = []
    if info.deprecated:
        alert.append(f"\N{WARNING SIGN}\N{VARIATION SELECTOR-16} {safe(info.deprecated, 300)}")
    if info.warning:
        alert.append(f"\N{WARNING SIGN}\N{VARIATION SELECTOR-16} {info.warning}")

    top = header(
        f"[{safe(info.name, 100)}]({info.url})",
        DOT.join([eco.label, f"v{safe(info.version, 30)}", *badges]),
        description,
        thumbnail=eco.icon,
    )

    stat_parts = []
    if info.downloads is not None:
        stat_parts.append(f"\N{INBOX TRAY} **{compact(info.downloads)}** downloads ({info.downloads_label})")
    if info.release_count:
        stat_parts.append(f"\N{PACKAGE} **{info.release_count:,}** releases")
    if info.dependencies is not None:
        stat_parts.append(f"\N{LINK SYMBOL} **{info.dependencies}** dependencies")
    if info.size:
        stat_parts.append(f"\N{FLOPPY DISK} **{file_size(info.size)}**")
    stats = text(DOT.join(stat_parts)) if stat_parts else None

    homepage = info.homepage if info.homepage != info.repository else None
    details = facts(
        ("Author", safe(info.author, 80) if info.author else None),
        ("License", safe(info.license, 60) if info.license else None),
        (f"Requires {eco.requires_label}", f"`{truncate(info.requires, 40)}`" if info.requires else None),
        ("Latest release", dated(info.released)),
        ("First release", dated(info.first_release)),
        ("Homepage", homepage if valid_url(homepage) else None),
        ("Repository", info.repository if valid_url(info.repository) else None),
        *info.facts,
    )
    keywords = text(" ".join(f"`{word}`" for word in info.keywords)) if info.keywords else None
    install = text(f"```sh\n{eco.install.format(name=info.name)}\n```")

    return collect(top, text("\n".join(alert)) if alert else None, discord.ui.Separator(), stats, details, keywords, install)


def version_line(entry: VersionEntry, latest: str | None) -> str:
    parts = [f"`{truncate(entry.version, 30)}`"]
    if entry.version == latest:
        parts.append("**latest**")
    parts.extend(f"**{tag}**" for tag in entry.tags if (tag != "latest" and entry.version != latest) or (tag not in {"latest"} and tag != ""))
    if entry.prerelease:
        parts.append("\N{TEST TUBE} pre-release")
    if entry.yanked:
        parts.append("\N{NO ENTRY SIGN} yanked")
    if entry.deprecated:
        parts.append("\N{WARNING SIGN}\N{VARIATION SELECTOR-16} deprecated")
    if stamp := when(entry.released):
        parts.append(stamp)
    if entry.note:
        parts.append(entry.note)
    return DOT.join(dict.fromkeys(parts))


def versions_items(eco: Ecosystem, vlist: VersionList, chunk: list[VersionEntry]) -> list[discord.ui.Item]:
    subtitle = f"{eco.label}{DOT}{vlist.total:,} release{'' if vlist.total == 1 else 's'}"
    if vlist.latest:
        subtitle += f"{DOT}latest `{truncate(vlist.latest, 30)}`"
    shown = len(vlist.entries)
    note = f"-# Showing the newest {shown} of {vlist.total:,} releases" if vlist.total > shown else None
    return collect(
        header(f"{safe(vlist.name, 100)} versions", subtitle, thumbnail=eco.icon),
        discord.ui.Separator(),
        text("\n".join(version_line(entry, vlist.latest) for entry in chunk)),
        text(note) if note else None,
    )


def dependency_items(eco: Ecosystem, deps: DependencyList) -> list[discord.ui.Item]:
    total = sum(len(entries) for entries in deps.groups.values())
    subtitle = f"{eco.label}{DOT}v{safe(deps.version, 30)}{DOT}{total} declared"
    details = facts((f"Requires {eco.requires_label}", f"`{truncate(deps.requires, 40)}`" if deps.requires else None))

    blocks: list[discord.ui.Item] = []
    remaining = DEPENDENCY_BUDGET
    groups = list(deps.groups.items())
    for title, entries in groups[:MAX_GROUPS]:
        if remaining < 80:
            break
        block = pack(entries, min(GROUP_BUDGET, remaining))
        remaining -= len(block)
        blocks.append(text(f"**{safe(title, 60)}** ({len(entries)})\n{block}"))
    if len(groups) > len(blocks):
        blocks.append(text(f"-# and {len(groups) - len(blocks)} more group{'' if len(groups) - len(blocks) == 1 else 's'} not shown"))
    if not groups:
        blocks.append(text("*This version declares no dependencies.*"))

    return collect(header(f"{safe(deps.name, 100)} dependencies", subtitle, thumbnail=eco.icon), discord.ui.Separator(), details, *blocks)


def search_items(eco: Ecosystem, query: str, result: SearchResult) -> list[discord.ui.Item]:
    subtitle = f"{eco.label}{DOT}results for {code(query, 40)}"
    if result.total:
        subtitle += f"{DOT}{result.total:,} total"

    blocks = []
    for hit in result.hits:
        title = f"**[{safe(hit.name, 80)}]({hit.url})**" + (f" `{truncate(hit.version, 20)}`" if hit.version else "")
        lines = [title]
        if hit.description:
            lines.append(safe(hit.description, 120))
        meta = [part for part in (hit.detail, f"updated {when(hit.updated)}" if when(hit.updated) else None) if part]
        if meta:
            lines.append(f"-# {DOT.join(meta)}")
        blocks.append("\n".join(lines))

    return collect(
        header(f"{eco.label} search", subtitle, thumbnail=eco.icon),
        discord.ui.Separator(),
        text("\n\n".join(blocks)),
        text(f"-# {result.note}") if result.note else None,
    )


def compare_table(first: PackageInfo, second: PackageInfo) -> str:
    def cell(value: object | None, width: int = 18) -> str:
        return truncate(str(value), width) if value not in {None, ""} else "\N{EM DASH}"

    eco = first.ecosystem
    rows = [
        ("Version", f"v{first.version}", f"v{second.version}"),
        ("Latest release", day(first.released), day(second.released)),
        ("First release", day(first.first_release), day(second.first_release)),
        ("Releases", first.release_count, second.release_count),
        ("Dependencies", first.dependencies, second.dependencies),
        (
            "Downloads",
            compact(first.downloads) if first.downloads is not None else None,
            compact(second.downloads) if second.downloads is not None else None,
        ),
        ("Size", file_size(first.size) if first.size else None, file_size(second.size) if second.size else None),
        ("License", first.license, second.license),
        (f"Needs {eco.requires_label}", first.requires, second.requires),
    ]
    width = max(len(label) for label, _, _ in rows)
    lines = [f"{'':<{width}}  {cell(first.name):<18}  {cell(second.name):<18}"]
    lines += [f"{label:<{width}}  {cell(left):<18}  {cell(right):<18}" for label, left, right in rows]
    return "```\n" + "\n".join(lines) + "\n```"


def highlights(first: PackageInfo, second: PackageInfo) -> list[str]:
    def name(info: PackageInfo) -> str:
        return f"**{safe(info.name, 40)}**"

    lines: list[str] = []
    if first.downloads and second.downloads and first.downloads_label == second.downloads_label and first.downloads != second.downloads:
        big, small = (first, second) if first.downloads > second.downloads else (second, first)
        downloads = big.downloads / small.downloads if big.downloads and small.downloads else 0

        lines.append(f"\N{INBOX TRAY} {name(big)} has {downloads:.1f}\N{MULTIPLICATION SIGN} the downloads ({first.downloads_label}).")

    released = (parse_time(first.released), parse_time(second.released))
    if released[0] and released[1] and released[0] != released[1]:
        lines.append(f"\N{CALENDAR} {name(first if released[0] > released[1] else second)} was released more recently.")

    started = (parse_time(first.first_release), parse_time(second.first_release))
    if started[0] and started[1] and started[0] != started[1]:
        lines.append(f"\N{HOURGLASS WITH FLOWING SAND} {name(first if started[0] < started[1] else second)} is the older project.")

    if first.dependencies is not None and second.dependencies is not None and first.dependencies != second.dependencies:
        fewer = first if first.dependencies < second.dependencies else second
        lines.append(f"\N{LINK SYMBOL} {name(fewer)} has fewer dependencies ({first.dependencies} vs {second.dependencies}).")

    if first.size and second.size and first.size != second.size:
        smaller = first if first.size < second.size else second
        lines.append(f"\N{FLOPPY DISK} {name(smaller)} is smaller ({file_size(first.size)} vs {file_size(second.size)}).")
    return lines


def compare_items(first: PackageInfo, second: PackageInfo) -> list[discord.ui.Item]:
    eco = first.ecosystem
    notes = highlights(first, second)
    footer = (
        f"-# Downloads cover the {first.downloads_label}"
        + (" (from pypistats.org)" if eco is PYPI else "")
        + ". Dependencies count runtime requirements only."
    )
    return collect(
        header(f"{safe(first.name, 60)} vs {safe(second.name, 60)}", eco.label, thumbnail=eco.icon),
        discord.ui.Separator(),
        text(compare_table(first, second)),
        text("\n".join(notes)) if notes else None,
        text(footer),
    )


class Packages(commands.Cog, name="Packages"):
    """Look up, compare and search packages on PyPI, npm and crates.io."""

    help_emoji = "\N{PACKAGE}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        fetch = Fetcher(bot.http_session)
        self.registries: dict[Ecosystem, Registry] = {
            PYPI: PyPIRegistry(fetch),
            NPM: NpmRegistry(fetch),
            CRATES: CratesRegistry(fetch),
        }

    async def deliver(self, ctx: commands.Context[Bot], producer: Awaitable[PackageView]) -> discord.Message:
        none = discord.AllowedMentions.none()
        async with ctx.typing():
            try:
                view = await producer
            except RegistryError as error:
                return await ctx.reply(view=NoticeLayout.error(str(error), title="Packages"), allowed_mentions=none)

        message = await ctx.reply(view=view, allowed_mentions=none)
        view.message = message
        return message

    @staticmethod
    def single(ctx: commands.Context[Bot], page: Page) -> PackageView:
        return PackageView(ctx.author, [page])

    async def info_view(self, ctx: commands.Context[Bot], eco: Ecosystem, package: str) -> PackageView:
        registry = self.registries[eco]
        info = await registry.info(registry.validate(package))

        links: list[tuple[str, str]] = []
        if info.homepage and info.homepage != info.repository:
            links.append(("Homepage", info.homepage))
        if info.repository:
            links.append(("Repository", info.repository))
        if info.documentation:
            links.append(("Documentation", info.documentation))
        links.extend(info.extra_links)
        return self.single(ctx, Page(partial(info_items, info), url=info.url, label=f"Open on {eco.label}", colour=eco.colour, links=links))

    async def versions_view(self, ctx: commands.Context[Bot], eco: Ecosystem, package: str) -> PackageView:
        registry = self.registries[eco]
        vlist = await registry.versions(registry.validate(package))
        if not vlist.entries:
            msg = f"`{vlist.name}` has no published versions."
            raise RegistryError(msg)

        vlist.entries = vlist.entries[:MAX_VERSIONS]
        pages = [
            Page(
                partial(versions_items, eco, vlist, vlist.entries[start : start + VERSIONS_PER_PAGE]),
                url=vlist.url,
                label=f"Open on {eco.label}",
                colour=eco.colour,
            )
            for start in range(0, len(vlist.entries), VERSIONS_PER_PAGE)
        ]
        return PackageView(ctx.author, pages)

    async def dependencies_view(self, ctx: commands.Context[Bot], eco: Ecosystem, package: str, version: str | None) -> PackageView:
        registry = self.registries[eco]
        deps = await registry.dependencies(registry.validate(package), registry.validate_version(version))
        return self.single(ctx, Page(partial(dependency_items, eco, deps), url=deps.url, label=f"Open on {eco.label}", colour=eco.colour))

    @commands.group(name="pypisearch", aliases=["pypi"], invoke_without_command=True, extras={"examples": ["pypisearch requests"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pypisearch(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The package to search for."),
    ) -> discord.Message:
        """Get info about a Python package directly from PyPi."""
        return await self.deliver(ctx, self.info_view(ctx, PYPI, package))

    @pypisearch.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["pypisearch versions requests"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pypi_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The package whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a Python package, newest first."""
        return await self.deliver(ctx, self.versions_view(ctx, PYPI, package))

    @pypisearch.command(
        name="dependencies",
        aliases=["dependency", "deps", "requires"],
        extras={"examples": ["pypisearch dependencies requests", "pypisearch deps requests 2.31.0"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pypi_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the dependencies a Python package declares, including optional extras."""
        return await self.deliver(ctx, self.dependencies_view(ctx, PYPI, package, version))

    @commands.group(name="npmsearch", aliases=["npm"], invoke_without_command=True, extras={"examples": ["npmsearch react", "npmsearch @types/node"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def npmsearch(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The package to search for."),
    ) -> discord.Message:
        """Get info about a NPM package directly from the NPM Registry."""
        return await self.deliver(ctx, self.info_view(ctx, NPM, package))

    @npmsearch.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["npmsearch versions react"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def npm_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The package whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of an npm package, newest first, with their dist-tags."""
        return await self.deliver(ctx, self.versions_view(ctx, NPM, package))

    @npmsearch.command(
        name="deps",
        aliases=["dependencies", "dependency"],
        extras={"examples": ["npmsearch deps express", "npmsearch deps express 4.18.2"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def npm_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version or dist-tag. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the dependencies, peer dependencies and dev dependencies of an npm package."""
        return await self.deliver(ctx, self.dependencies_view(ctx, NPM, package, version))

    @commands.group(name="crate", aliases=["crates"], invoke_without_command=True, extras={"examples": ["crate serde"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def crate(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The package to search for."),
    ) -> discord.Message:
        """Get info about a Rust package directly from the Crates.IO Registry."""
        return await self.deliver(ctx, self.info_view(ctx, CRATES, package))

    @crate.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["crate versions serde"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def crate_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The crate whose published versions to list."),
    ) -> discord.Message:
        """Shows the published versions of a Rust crate, including yanked ones."""
        return await self.deliver(ctx, self.versions_view(ctx, CRATES, package))

    @crate.command(name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["crate deps serde", "crate deps serde 1.0.200"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def crate_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The crate whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest stable one."),
    ) -> discord.Message:
        """Shows the normal, optional, build and dev dependencies of a Rust crate."""
        return await self.deliver(ctx, self.dependencies_view(ctx, CRATES, package, version))

    @commands.group(name="package", aliases=["pkg"], invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package(self, ctx: commands.Context[Bot]) -> discord.Message | None:
        """Compare and search packages across PyPI, npm and crates.io."""
        return await ctx.send_help(ctx.command)

    @package.command(
        name="compare",
        aliases=["vs", "diff"],
        extras={"examples": ["package compare pypi requests httpx", "package compare npm express fastify", "package compare crates reqwest ureq"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package_compare(
        self,
        ctx: commands.Context[Bot],
        ecosystem: Annotated[Ecosystem, EcosystemConverter] = commands.parameter(  # noqa: B008
            converter=EcosystemConverter,
            description="Where the packages live: `pypi`, `npm` or `crates`.",
        ),
        first: str = commands.parameter(description="The first package."),
        second: str = commands.parameter(description="The second package."),
    ) -> discord.Message:
        """Compares the metadata of two packages from the same ecosystem side by side."""
        return await self.deliver(ctx, self.compare_view(ctx, ecosystem, first, second))

    async def compare_view(self, ctx: commands.Context[Bot], eco: Ecosystem, first: str, second: str) -> PackageView:
        registry = self.registries[eco]
        first, second = registry.validate(first), registry.validate(second)
        if first.casefold() == second.casefold():
            msg = "Pick two different packages to compare."
            raise RegistryError(msg)

        left, right = await asyncio.gather(registry.info(first), registry.info(second))
        return self.single(
            ctx,
            Page(
                partial(compare_items, left, right),
                url=left.url,
                label=truncate(f"Open {left.name}", 80),
                colour=eco.colour,
                links=[(truncate(f"Open {right.name}", 80), right.url)],
            ),
        )

    @package.command(
        name="search",
        aliases=["find", "s"],
        extras={"examples": ["package search pypi http client", "package search npm date library", "package search crates async runtime"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package_search(
        self,
        ctx: commands.Context[Bot],
        ecosystem: Annotated[Ecosystem, EcosystemConverter] = commands.parameter(  # noqa: B008
            converter=EcosystemConverter,
            description="Where to search: `pypi`, `npm` or `crates`.",
        ),
        *,
        query: str = commands.parameter(description="What to look for."),
    ) -> discord.Message:
        """Searches a package registry for packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, ecosystem, query))

    async def search_view(self, ctx: commands.Context[Bot], eco: Ecosystem, query: str) -> PackageView:
        query = " ".join(query.split())
        if not query or len(query) > 100:
            msg = "The search query must be between 1 and 100 characters."
            raise RegistryError(msg)

        result = await self.registries[eco].search(query)
        return self.single(ctx, Page(partial(search_items, eco, query, result), url=None, colour=eco.colour))
