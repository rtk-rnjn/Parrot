from __future__ import annotations

import abc
import asyncio
import json
import re
from dataclasses import dataclass, field
from email.utils import parseaddr
from functools import partial
from typing import TYPE_CHECKING, Annotated, Any, ClassVar
from urllib.parse import quote

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import commands
from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import InvalidVersion, Version

from core.utils import BaseLayoutView, NoticeLayout, code, dated, file_size, parse_time, safe, truncate, valid_url, when

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from core import Bot

__all__ = ("Packages",)

TIMEOUT = aiohttp.ClientTimeout(total=15)
MAX_RESPONSE = 8 * 1024 * 1024
MAX_PACKUMENT = 30 * 1024 * 1024  # the full npm document of a package can be huge

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DiscordPackageBot/1.0; +https://discord.com)",
    "Accept": "application/json, text/plain, */*",
}

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

GO_MOD_DIRECTIVE = re.compile(r"^go\s+(\S+)", re.MULTILINE)
GO_REQUIRE_BLOCK = re.compile(r"require\s*\((.*?)\)", re.DOTALL)
GO_REQUIRE_SINGLE = re.compile(r"^require\s+([^\s(]\S*)\s+(\S+)(.*)$", re.MULTILINE)


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
        return self.page.format(name=quote(name, safe="@/:"))


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
    aliases=("crates", "crate", "cargo", "rust", "rs"),
    page="https://crates.io/crates/{name}",
)
GO = Ecosystem(
    key="go",
    label="pkg.go.dev",
    colour=discord.Colour(0x00ADD8),
    icon="https://go.dev/blog/go-brand/Go-Logo/PNG/Go-Logo_Blue.png",
    install="go get {name}",
    requires_label="Go",
    name_pattern=re.compile(r"[A-Za-z0-9][A-Za-z0-9._~/-]{0,127}"),
    aliases=("go", "golang", "godev", "gomod", "gopkg"),
    page="https://pkg.go.dev/{name}",
)
PACKAGIST = Ecosystem(
    key="packagist",
    label="Packagist",
    colour=discord.Colour(0xF28D1A),
    icon="https://packagist.org/img/logo-small.png",
    install="composer require {name}",
    requires_label="PHP",
    name_pattern=re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?(?:/[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)?"),
    aliases=("packagist", "composer", "php"),
    page="https://packagist.org/packages/{name}",
)
RUBYGEMS = Ecosystem(
    key="rubygems",
    label="RubyGems",
    colour=discord.Colour(0xE9573F),
    icon="https://rubygems.org/favicon.ico",
    install="gem install {name}",
    requires_label="Ruby",
    name_pattern=re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}"),
    aliases=("rubygems", "gem", "gems", "ruby", "rb"),
    page="https://rubygems.org/gems/{name}",
)
NUGET = Ecosystem(
    key="nuget",
    label="NuGet",
    colour=discord.Colour(0x004880),
    icon="https://www.nuget.org/Content/gallery/img/logo-og-600x600.png",
    install="dotnet add package {name}",
    requires_label=".NET",
    name_pattern=re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}"),
    aliases=("nuget", "dotnet", "csharp", "cs", "net"),
    page="https://www.nuget.org/packages/{name}",
)
PUB = Ecosystem(
    key="pub",
    label="pub.dev",
    colour=discord.Colour(0x0175C2),
    icon="https://pub.dev/static/hash-6pt3begn/img/pub-dev-icon-cover-image.png",
    install="dart pub add {name}",
    requires_label="Dart SDK",
    name_pattern=re.compile(r"[a-zA-Z0-9_]{1,64}"),
    aliases=("pub", "pubdev", "dart", "flutter"),
    page="https://pub.dev/packages/{name}",
)
HEX = Ecosystem(
    key="hex",
    label="Hex.pm",
    colour=discord.Colour(0x6E4A7E),
    icon="https://hex.pm/images/hex.png",
    install='{{:{name}, "~> {version}"}}',
    requires_label="Elixir",
    name_pattern=re.compile(r"[a-zA-Z0-9_]{1,64}"),
    aliases=("hex", "hexpm", "elixir", "ex", "erlang", "gleam"),
    page="https://hex.pm/packages/{name}",
)

ECOSYSTEMS = (PYPI, NPM, CRATES, GO, PACKAGIST, RUBYGEMS, NUGET, PUB, HEX)
ECOSYSTEM_NAMES = ", ".join(f"`{eco.key}`" for eco in ECOSYSTEMS)


class EcosystemConverter(commands.Converter[Ecosystem]):
    async def convert(self, ctx: commands.Context[Bot], argument: str) -> Ecosystem:
        wanted = argument.strip().casefold()
        for ecosystem in ECOSYSTEMS:
            if wanted == ecosystem.label.casefold() or wanted in ecosystem.aliases:
                return ecosystem
        msg = f"The ecosystem should be one of: {ECOSYSTEM_NAMES}."
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


def compact(number: int) -> str:
    for threshold, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "k")):
        if number >= threshold:
            return f"{number / threshold:.1f}".rstrip("0").rstrip(".") + suffix
    return str(number)


def day(iso: str | None) -> str | None:
    moment = parse_time(iso)
    return moment.strftime("%Y-%m-%d") if moment else None


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
        return value.get("name") or value.get("username") or None
    if isinstance(value, str):
        return re.split(r"\s*[<(]", value, maxsplit=1)[0].strip() or None
    return None


def prerelease(version: str) -> bool:
    cleaned = version.removeprefix("v")
    try:
        return Version(cleaned).is_prerelease
    except InvalidVersion:
        return "-" in cleaned or cleaned.startswith("dev-") or cleaned.endswith("-dev")


def version_key(version: str) -> tuple[int, Version, str]:
    cleaned = version.removeprefix("v")
    try:
        return (1, Version(cleaned), version)
    except InvalidVersion:
        return (0, Version("0"), version)


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
        merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
        try:
            async with self.session.get(url, params=params, headers=merged_headers, timeout=TIMEOUT) as response:
                status = response.status
                if status in (404, 410):
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
        expression = info.get("license_expression")
        if expression:
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
            extras = EXTRA_MARKER.findall(marker)
            if extras:
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


class GoRegistry(Registry):
    ecosystem = GO
    proxy = "https://proxy.golang.org"
    site = "https://pkg.go.dev"

    @staticmethod
    def escape_path(module: str) -> str:
        """Go module proxy escapes uppercase ASCII letters as ``!lowercase``."""
        return re.sub(r"[A-Z]", lambda m: f"!{m[0].lower()}", module)

    @staticmethod
    def parse_gomod(content: str) -> tuple[str | None, dict[str, list[str]]]:
        go_match = GO_MOD_DIRECTIVE.search(content)
        go_version = go_match[1] if go_match else None

        direct: list[str] = []
        indirect: list[str] = []

        def add_line(mod: str, ver: str, comment: str) -> None:
            entry = f"{mod}@{ver}"
            if "indirect" in comment:
                indirect.append(entry)
            else:
                direct.append(entry)

        for block in GO_REQUIRE_BLOCK.findall(content):
            for raw in block.splitlines():
                line, _, comment = raw.partition("//")
                parts = line.strip().split()
                if len(parts) >= 2:
                    add_line(parts[0], parts[1], comment)

        for match in GO_REQUIRE_SINGLE.finditer(content):
            add_line(match[1], match[2], match[3])

        groups: dict[str, list[str]] = {}
        if direct:
            groups["Direct dependencies"] = sorted(dict.fromkeys(direct), key=str.lower)
        if indirect:
            groups["Indirect dependencies"] = sorted(dict.fromkeys(indirect), key=str.lower)
        return go_version, groups

    @staticmethod
    def parse_pkg_page(html: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        synopsis_el = soup.select_one(".Documentation-overview p, p.UnitDoc-summary, meta[name='description']")
        synopsis = None
        if synopsis_el:
            synopsis = synopsis_el.get("content") if synopsis_el.name == "meta" else " ".join(synopsis_el.get_text().split())
            if synopsis and synopsis.startswith("Package ") and " - Go Packages" in synopsis:
                synopsis = None

        license_el = soup.select_one("[data-test-id='UnitHeader-license'] a, a[data-test-id='UnitHeader-license']")
        licence = license_el.get_text(strip=True) if license_el else None

        repo_el = soup.select_one(".UnitMeta-repo a[href]")
        repository = repo_el.get("href") if repo_el else None

        imported_el = soup.select_one("a[href*='tab=importedby']")
        imported_by = None
        if imported_el:
            digits = re.sub(r"[^\d]", "", imported_el.get_text())
            if digits.isdigit():
                imported_by = int(digits)

        return {
            "summary": synopsis,
            "license": licence,
            "repository": repository if isinstance(repository, str) else None,
            "imported_by": imported_by,
        }

    async def resolve_module(self, name: str) -> tuple[str, dict[str, Any]]:
        """Resolves either a full module path (`github.com/gin-gonic/gin`) or a short keyword (`gin`) via proxy & search."""
        cleaned = name.strip().strip("/")
        candidates = [cleaned]
        if "/" in cleaned and "." in cleaned.split("/", 1)[0]:
            parts = cleaned.split("/")
            candidates.extend("/".join(parts[:end]) for end in range(len(parts) - 1, 1, -1))

        for candidate in candidates:
            if "." not in candidate.split("/", 1)[0]:
                break
            escaped = self.escape_path(candidate)
            latest = await self.attempt(self.fetch.json(f"{self.proxy}/{escaped}/@latest", source="Go Module Proxy", missing=""))
            if isinstance(latest, dict) and latest.get("Version"):
                return candidate, latest

        # If a short name (like `gin`, `cobra`, `viper`) was given, search pkg.go.dev and resolve the top module.
        search_res = await self.attempt(self.search(cleaned))
        if search_res and search_res.hits:
            top_path = search_res.hits[0].name
            escaped = self.escape_path(top_path)
            latest = await self.attempt(self.fetch.json(f"{self.proxy}/{escaped}/@latest", source="Go Module Proxy", missing=""))
            if isinstance(latest, dict) and latest.get("Version"):
                return top_path, latest
            # Standard library package (e.g. `net/http`, `fmt`)
            hit = search_res.hits[0]
            return hit.name, {"Version": (hit.version or "std").removeprefix("v"), "Time": None, "Synopsis": hit.description, "Std": True}

        msg = f"`{name}` was not found on pkg.go.dev or the Go Module Proxy."
        raise RegistryError(msg)

    async def info(self, name: str) -> PackageInfo:
        module, latest = await self.resolve_module(name)
        version = str(latest["Version"]).removeprefix("v")
        escaped = self.escape_path(module)

        if latest.get("Std"):
            page_html = await self.attempt(self.fetch.text(f"{self.site}/{module}", source="pkg.go.dev", missing=""))
            meta = await asyncio.to_thread(self.parse_pkg_page, page_html) if page_html else {}
            return PackageInfo(
                ecosystem=GO,
                name=module,
                version=version,
                url=GO.page_url(module),
                summary=meta.get("summary") or latest.get("Synopsis"),
                license=meta.get("license") or "BSD-3-Clause",
                repository=meta.get("repository") or "https://cs.opensource.google/go/go",
                documentation=GO.page_url(module),
                facts=[("Imported by", f"{meta['imported_by']:,} packages")] if meta.get("imported_by") is not None else [],
            )

        vlist_raw, gomod_raw, page_html = await asyncio.gather(
            self.attempt(self.fetch.text(f"{self.proxy}/{escaped}/@v/list", source="Go Module Proxy", missing="")),
            self.attempt(self.fetch.text(f"{self.proxy}/{escaped}/@v/v{version}.mod", source="Go Module Proxy", missing="")),
            self.attempt(self.fetch.text(f"{self.site}/{module}", source="pkg.go.dev", missing="")),
        )
        all_versions = [line.strip() for line in (vlist_raw or "").splitlines() if line.strip()]
        all_versions.sort(key=version_key)
        first_release = None
        if all_versions:
            first_info = await self.attempt(
                self.fetch.json(f"{self.proxy}/{escaped}/@v/{quote(all_versions[0], safe='')}.info", source="Go Module Proxy", missing="")
            )
            if isinstance(first_info, dict):
                first_release = first_info.get("Time")

        go_ver, dep_groups = self.parse_gomod(gomod_raw) if gomod_raw else (None, {})
        direct_deps = len(dep_groups.get("Direct dependencies", [])) if gomod_raw else None
        meta = await asyncio.to_thread(self.parse_pkg_page, page_html) if page_html else {}

        repo = meta.get("repository")
        if not repo and module.startswith(("github.com/", "gitlab.com/", "bitbucket.org/", "codeberg.org/")):
            parts = module.split("/")
            if len(parts) >= 3:
                repo = f"https://{parts[0]}/{parts[1]}/{parts[2]}"

        facts_list: list[tuple[str, str]] = []
        if meta.get("imported_by") is not None:
            facts_list.append(("Imported by", f"{meta['imported_by']:,} packages"))

        return PackageInfo(
            ecosystem=GO,
            name=module,
            version=version,
            url=GO.page_url(module),
            summary=meta.get("summary"),
            license=meta.get("license"),
            repository=repo,
            documentation=GO.page_url(module),
            released=latest.get("Time"),
            first_release=first_release,
            release_count=len(all_versions) or None,
            dependencies=direct_deps,
            requires=go_ver,
            facts=facts_list,
        )

    async def versions(self, name: str) -> VersionList:
        module, latest = await self.resolve_module(name)
        escaped = self.escape_path(module)
        raw = await self.attempt(self.fetch.text(f"{self.proxy}/{escaped}/@v/list", source="Go Module Proxy", missing=""))
        versions = [line.strip() for line in (raw or "").splitlines() if line.strip()]
        latest_ver = str(latest.get("Version") or "").removeprefix("v")
        if not versions and latest_ver:
            versions = [f"v{latest_ver}"]

        versions.sort(key=version_key, reverse=True)
        top_versions = versions[:VERSIONS_PER_PAGE]
        infos = await asyncio.gather(
            *(
                self.attempt(self.fetch.json(f"{self.proxy}/{escaped}/@v/{quote(ver, safe='')}.info", source="Go Module Proxy", missing=""))
                for ver in top_versions
            )
        )
        timestamps = {ver: (info.get("Time") if isinstance(info, dict) else None) for ver, info in zip(top_versions, infos, strict=False)}
        if f"v{latest_ver}" in timestamps and not timestamps[f"v{latest_ver}"]:
            timestamps[f"v{latest_ver}"] = latest.get("Time")

        entries = [
            VersionEntry(
                ver.removeprefix("v"),
                timestamps.get(ver),
                prerelease(ver),
            )
            for ver in versions
        ]
        return VersionList(module, latest_ver or None, entries, len(entries), f"{GO.page_url(module)}?tab=versions")

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        module, latest = await self.resolve_module(name)
        escaped = self.escape_path(module)
        resolved = version or str(latest.get("Version") or "").removeprefix("v")
        tag = resolved if resolved.startswith("v") else f"v{resolved}"

        gomod = await self.fetch.text(
            f"{self.proxy}/{escaped}/@v/{quote(tag, safe='')}.mod",
            source="Go Module Proxy",
            missing=f"Version `{resolved}` of `{module}` was not found on the Go Module Proxy.",
        )
        go_ver, groups = self.parse_gomod(gomod)
        return DependencyList(module, resolved.removeprefix("v"), groups, f"{GO.page_url(module)}?tab=imports", go_ver)

    async def search(self, query: str) -> SearchResult:
        html = await self.fetch.text(
            f"{self.site}/search",
            params={"q": query, "m": "package", "limit": SEARCH_LIMIT},
            headers={"Accept": "text/html"},
            source="pkg.go.dev",
            missing="pkg.go.dev search is unavailable.",
        )
        hits = await asyncio.to_thread(self.parse_search, html)
        if not hits:
            msg = f"No Go packages matched {code(query)} on pkg.go.dev."
            raise RegistryError(msg)
        return SearchResult(hits)

    @classmethod
    def parse_search(cls, html: str) -> list[SearchHit]:
        soup = BeautifulSoup(html, "html.parser")
        hits: list[SearchHit] = []
        for card in soup.select("div.SearchSnippet")[:SEARCH_LIMIT]:
            link = card.select_one(".SearchSnippet-headerContainer h2 a[href]")
            if link is None:
                continue
            href = str(link.get("href") or "").strip("/")
            if not href:
                continue
            synopsis = card.select_one("p.SearchSnippet-synopsis")
            info_label = card.select_one("div.SearchSnippet-infoLabel")

            version = None
            details: list[str] = []
            if info_label:
                strongs = info_label.select("strong")
                if strongs:
                    first_strong = strongs[0].get_text(strip=True)
                    if first_strong.startswith(("v", "go")):
                        version = first_strong.removeprefix("v")
                imported = info_label.select_one("a[href*='importedby'] strong")
                if imported:
                    details.append(f"imported by {imported.get_text(strip=True)}")
                lic = info_label.select_one("[data-test-id='snippet-license'] a")
                if lic:
                    details.append(lic.get_text(strip=True))

            hits.append(
                SearchHit(
                    href,
                    version,
                    " ".join(synopsis.get_text().split()) if synopsis else None,
                    GO.page_url(href),
                    None,
                    DOT.join(details) or None,
                )
            )
        return hits


class PackagistRegistry(Registry):
    ecosystem = PACKAGIST
    base = "https://packagist.org"

    async def resolve_package(self, name: str) -> dict[str, Any]:
        cleaned = name.strip().strip("/").lower()
        if "/" in cleaned:
            data = await self.fetch.json(
                f"{self.base}/packages/{cleaned}.json",
                source="Packagist",
                missing=f"`{cleaned}` was not found on Packagist.",
            )
            return data["package"]

        # Short name convenience: try `name/name` first (e.g. `monolog` -> `monolog/monolog`), then top search result.
        same = await self.attempt(self.fetch.json(f"{self.base}/packages/{cleaned}/{cleaned}.json", source="Packagist", missing=""))
        if isinstance(same, dict) and "package" in same:
            return same["package"]

        searched = await self.attempt(
            self.fetch.json(f"{self.base}/search.json", params={"q": cleaned, "per_page": 1}, source="Packagist", missing="")
        )
        results = (searched or {}).get("results") or []
        if results and results[0].get("name"):
            full_name = results[0]["name"]
            data = await self.fetch.json(
                f"{self.base}/packages/{full_name}.json",
                source="Packagist",
                missing=f"`{name}` was not found on Packagist.",
            )
            return data["package"]

        msg = f"`{name}` was not found on Packagist. Use `vendor/package` (e.g. `laravel/framework`)."
        raise RegistryError(msg)

    @staticmethod
    def pick_default_version(versions: dict[str, dict[str, Any]]) -> dict[str, Any]:
        tagged = [meta for ver, meta in versions.items() if not ver.startswith("dev-") and not ver.endswith("-dev")]
        if tagged:
            tagged.sort(key=lambda meta: version_key(str(meta.get("version", ""))), reverse=True)
            stable = [meta for meta in tagged if not prerelease(str(meta.get("version", "")))]
            return stable[0] if stable else tagged[0]
        all_metas = list(versions.values())
        all_metas.sort(key=lambda meta: meta.get("time") or "", reverse=True)
        return all_metas[0] if all_metas else {}

    async def info(self, name: str) -> PackageInfo:
        pkg = await self.resolve_package(name)
        versions: dict[str, dict[str, Any]] = pkg.get("versions") or {}
        latest = self.pick_default_version(versions)
        ver_str = str(latest.get("version") or "unknown").removeprefix("v")

        tagged_metas = [m for v, m in versions.items() if not v.startswith("dev-") and not v.endswith("-dev")]
        times = [m["time"] for m in (tagged_metas or versions.values()) if m.get("time")]

        require = latest.get("require") or {}
        php_req = require.get("php") or require.get("php-64bit")
        runtime_deps = sum(1 for k in require if k not in {"php", "php-64bit"} and not k.startswith("ext-"))

        authors = [person(a) for a in latest.get("authors") or []]
        authors = [a for a in authors if a]
        maintainers = [person(m) for m in pkg.get("maintainers") or []]
        maintainers = [m for m in maintainers if m]

        lic_list = latest.get("license") or []
        licence = ", ".join(lic_list) if isinstance(lic_list, list) and lic_list else (lic_list if isinstance(lic_list, str) else None)

        downloads = pkg.get("downloads") or {}
        abandoned = pkg.get("abandoned")
        deprecated_msg = None
        if abandoned:
            deprecated_msg = f"Abandoned — use `{abandoned}` instead." if isinstance(abandoned, str) else "This package is marked as abandoned."

        facts_list: list[tuple[str, str]] = []
        if downloads.get("total"):
            facts_list.append(("All-time installs", f"{downloads['total']:,}"))
        if pkg.get("favers"):
            facts_list.append(("Stars", f"{pkg['favers']:,}"))
        if pkg.get("type"):
            facts_list.append(("Type", str(pkg["type"])))
        if maintainers:
            facts_list.append(("Maintainers", ", ".join(maintainers[:5])))

        return PackageInfo(
            ecosystem=PACKAGIST,
            name=pkg["name"],
            version=ver_str,
            url=PACKAGIST.page_url(pkg["name"]),
            summary=latest.get("description") or pkg.get("description"),
            license=licence,
            author=authors[0] if authors else (maintainers[0] if maintainers else None),
            homepage=latest.get("homepage") or None,
            repository=normalize_repo(pkg.get("repository")),
            released=latest.get("time"),
            first_release=min(times, default=pkg.get("time")),
            release_count=len(tagged_metas) or len(versions) or None,
            dependencies=runtime_deps,
            downloads=downloads.get("monthly"),
            downloads_label="last 30 days",
            requires=php_req,
            keywords=[str(w) for w in (latest.get("keywords") or [])[:10] if w],
            deprecated=deprecated_msg,
            facts=facts_list,
        )

    async def versions(self, name: str) -> VersionList:
        pkg = await self.resolve_package(name)
        versions: dict[str, dict[str, Any]] = pkg.get("versions") or {}
        latest = self.pick_default_version(versions)
        latest_ver = str(latest.get("version") or "").removeprefix("v") or None

        tagged = [(ver, meta) for ver, meta in versions.items() if not ver.startswith("dev-") and not ver.endswith("-dev")]
        source_items = tagged if tagged else list(versions.items())
        entries = [
            VersionEntry(
                ver.removeprefix("v"),
                meta.get("time"),
                prerelease(ver),
                deprecated=bool(pkg.get("abandoned")),
            )
            for ver, meta in source_items
        ]
        entries.sort(key=lambda e: (version_key(e.version), e.released or ""), reverse=True)
        return VersionList(pkg["name"], latest_ver, entries, len(entries), PACKAGIST.page_url(pkg["name"]))

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        pkg = await self.resolve_package(name)
        versions: dict[str, dict[str, Any]] = pkg.get("versions") or {}
        if version:
            target = versions.get(version) or versions.get(f"v{version}") or versions.get(version.removeprefix("v"))
            if not target:
                msg = f"Version `{version}` of `{pkg['name']}` was not found on Packagist."
                raise RegistryError(msg)
        else:
            target = self.pick_default_version(versions)

        ver_str = str(target.get("version") or version or "latest").removeprefix("v")
        require = target.get("require") or {}
        php_req = require.get("php") or require.get("php-64bit")

        groups: dict[str, list[str]] = {}
        for dep, constraint in require.items():
            if dep in ("php", "php-64bit"):
                continue
            if dep.startswith("ext-"):
                groups.setdefault("PHP extensions", []).append(f"{dep}:{constraint}")
            else:
                groups.setdefault("Required", []).append(f"{dep}:{constraint}")

        for dep, constraint in (target.get("require-dev") or {}).items():
            groups.setdefault("Dev dependencies", []).append(f"{dep}:{constraint}")

        for dep in target.get("suggest") or {}:
            groups.setdefault("Suggested", []).append(dep)

        order = ("Required", "PHP extensions", "Dev dependencies", "Suggested")
        ordered = {title: sorted(groups[title], key=str.lower) for title in order if title in groups}
        return DependencyList(pkg["name"], ver_str, ordered, PACKAGIST.page_url(pkg["name"]), php_req)

    async def search(self, query: str) -> SearchResult:
        data = await self.fetch.json(
            f"{self.base}/search.json",
            params={"q": query, "per_page": SEARCH_LIMIT},
            source="Packagist",
            missing="Packagist search is unavailable.",
        )
        hits: list[SearchHit] = []
        for entry in (data.get("results") or [])[:SEARCH_LIMIT]:
            details: list[str] = []
            if entry.get("downloads") is not None:
                details.append(f"{compact(entry['downloads'])} installs")
            if entry.get("favers"):
                details.append(f"\N{BLACK STAR} {compact(entry['favers'])}")
            hits.append(
                SearchHit(
                    entry["name"],
                    None,
                    entry.get("description"),
                    entry.get("url") or PACKAGIST.page_url(entry["name"]),
                    None,
                    DOT.join(details) or None,
                )
            )
        if not hits:
            msg = f"No PHP packages matched {code(query)} on Packagist."
            raise RegistryError(msg)
        return SearchResult(hits, data.get("total"))


class RubyGemsRegistry(Registry):
    ecosystem = RUBYGEMS
    base = "https://rubygems.org/api/v1"

    async def gem(self, name: str) -> dict[str, Any]:
        return await self.fetch.json(
            f"{self.base}/gems/{quote(name, safe='')}.json",
            source="RubyGems",
            missing=f"The gem `{name}` was not found on RubyGems.",
        )

    async def gem_versions(self, name: str) -> list[dict[str, Any]]:
        data = await self.fetch.json(
            f"{self.base}/versions/{quote(name, safe='')}.json",
            source="RubyGems",
            missing=f"The gem `{name}` was not found on RubyGems.",
        )
        return data if isinstance(data, list) else []

    async def info(self, name: str) -> PackageInfo:
        data, vlist = await asyncio.gather(
            self.gem(name),
            self.attempt(self.gem_versions(name)),
        )
        versions = vlist or []
        times = [entry["created_at"] for entry in versions if entry.get("created_at")]
        deps = (data.get("dependencies") or {}).get("runtime") or []
        licenses = data.get("licenses") or []
        licence = ", ".join(licenses) if isinstance(licenses, list) and licenses else None

        ruby_req = data.get("required_ruby_version")
        if ruby_req in (">= 0", ">= 0.0.0"):
            ruby_req = None

        facts_list: list[tuple[str, str]] = []
        if data.get("downloads"):
            facts_list.append(("All-time downloads", f"{data['downloads']:,}"))

        return PackageInfo(
            ecosystem=RUBYGEMS,
            name=data["name"],
            version=str(data.get("version") or "unknown"),
            url=data.get("project_uri") or RUBYGEMS.page_url(data["name"]),
            summary=data.get("info"),
            license=licence,
            author=data.get("authors") or None,
            homepage=data.get("homepage_uri") or None,
            repository=normalize_repo(data.get("source_code_uri")),
            documentation=data.get("documentation_uri") or None,
            released=data.get("version_created_at") or (versions[0].get("created_at") if versions else None),
            first_release=min(times, default=None),
            release_count=len(versions) or None,
            dependencies=len(deps),
            downloads=data.get("version_downloads"),
            downloads_label="this version",
            requires=ruby_req,
            yanked=bool(data.get("yanked")),
            facts=facts_list,
        )

    async def versions(self, name: str) -> VersionList:
        versions = await self.gem_versions(name)
        entries = [
            VersionEntry(
                str(entry["number"]),
                entry.get("created_at"),
                bool(entry.get("prerelease")),
                yanked=bool(entry.get("yanked")),
                note=f"{compact(entry['downloads_count'])} downloads" if entry.get("downloads_count") else None,
            )
            for entry in versions
            if entry.get("number")
        ]
        latest = next((e.version for e in entries if not e.prerelease and not e.yanked), entries[0].version if entries else None)
        return VersionList(name, latest, entries, len(entries), f"{RUBYGEMS.page_url(name)}/versions")

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        if version:
            data = await self.fetch.json(
                f"https://rubygems.org/api/v2/rubygems/{quote(name, safe='')}/versions/{quote(version, safe='')}.json",
                source="RubyGems",
                missing=f"Version `{version}` of `{name}` was not found on RubyGems.",
            )
        else:
            data = await self.gem(name)

        deps = data.get("dependencies") or {}
        groups: dict[str, list[str]] = {}
        for title, key in (("Runtime dependencies", "runtime"), ("Development dependencies", "development")):
            items = deps.get(key) or []
            if items:
                groups[title] = sorted((f"{item['name']} ({item.get('requirements', '')})" for item in items if item.get("name")), key=str.lower)

        ruby_req = data.get("required_ruby_version")
        if ruby_req in (">= 0", ">= 0.0.0"):
            ruby_req = None
        return DependencyList(
            data.get("name", name), str(data.get("version") or version or "latest"), groups, RUBYGEMS.page_url(data.get("name", name)), ruby_req
        )

    async def search(self, query: str) -> SearchResult:
        data = await self.fetch.json(
            f"{self.base}/search.json",
            params={"query": query},
            source="RubyGems",
            missing="RubyGems search is unavailable.",
        )
        if not isinstance(data, list) or not data:
            msg = f"No gems matched {code(query)} on RubyGems."
            raise RegistryError(msg)

        hits = [
            SearchHit(
                entry["name"],
                str(entry.get("version") or ""),
                entry.get("info"),
                entry.get("project_uri") or RUBYGEMS.page_url(entry["name"]),
                entry.get("version_created_at"),
                f"{compact(entry['downloads'])} downloads" if entry.get("downloads") else None,
            )
            for entry in data[:SEARCH_LIMIT]
            if entry.get("name")
        ]
        return SearchResult(hits, len(data))


class NuGetRegistry(Registry):
    ecosystem = NUGET
    search_url = "https://azuresearch-usnc.nuget.org/query"
    reg_base = "https://api.nuget.org/v3/registration5-gz-semver2"

    async def registration(self, name: str) -> tuple[str, list[dict[str, Any]]]:
        index = await self.fetch.json(
            f"{self.reg_base}/{quote(name.lower(), safe='')}/index.json",
            source="NuGet",
            missing=f"`{name}` was not found on NuGet.",
        )
        pages = index.get("items") or []
        if not pages:
            msg = f"`{name}` has no published versions on NuGet."
            raise RegistryError(msg)

        # Fetch the last page (and first page if separate) when items aren't inlined.
        leaves: list[dict[str, Any]] = []
        to_inspect = [pages[0], pages[-1]] if len(pages) > 1 else [pages[0]]
        resolved_pages: list[dict[str, Any]] = []
        for page in to_inspect:
            if "items" in page:
                resolved_pages.append(page)
            elif page.get("@id"):
                fetched = await self.attempt(self.fetch.json(page["@id"], source="NuGet", missing=""))
                if isinstance(fetched, dict):
                    resolved_pages.append(fetched)

        for page in resolved_pages:
            leaves.extend(page.get("items") or [])

        canonical = (leaves[-1].get("catalogEntry") or {}).get("id") if leaves else name
        return canonical or name, leaves

    async def info(self, name: str) -> PackageInfo:
        (_, leaves), search_data = await asyncio.gather(
            self.registration(name),
            self.attempt(
                self.fetch.json(self.search_url, params={"q": f"packageid:{name}", "take": 1, "prerelease": "true"}, source="NuGet", missing="")
            ),
        )
        if not leaves:
            msg = f"`{name}` was not found on NuGet."
            raise RegistryError(msg)

        catalog = leaves[-1].get("catalogEntry") or {}
        first_catalog = leaves[0].get("catalogEntry") or {}
        search_hit = (
            ((search_data or {}).get("data") or [{}])[0]
            if isinstance((search_data or {}).get("data"), list) and (search_data or {}).get("data")
            else {}
        )

        dep_groups = catalog.get("dependencyGroups") or []
        dep_names = {dep.get("id") for group in dep_groups for dep in (group.get("dependencies") or []) if isinstance(dep, dict) and dep.get("id")}
        frameworks = [group.get("targetFramework") for group in dep_groups if group.get("targetFramework")]

        authors = catalog.get("authors")
        if isinstance(authors, list):
            authors = ", ".join(authors)

        deprecation = catalog.get("deprecation") or {}
        deprecated_msg = None
        if deprecation:
            reasons = ", ".join(deprecation.get("reasons") or ["Deprecated"])
            alt = (deprecation.get("alternatePackage") or {}).get("id")
            deprecated_msg = f"{reasons}" + (f" — use `{alt}` instead." if alt else ".")

        total_versions = len(search_hit.get("versions") or []) or len(leaves)
        tags_raw = catalog.get("tags") or search_hit.get("tags") or []
        if isinstance(tags_raw, str):
            tags_raw = tags_raw.split()

        pkg_id = catalog.get("id") or search_hit.get("id") or name
        ver = catalog.get("version") or search_hit.get("version") or "unknown"

        return PackageInfo(
            ecosystem=NUGET,
            name=pkg_id,
            version=str(ver),
            url=NUGET.page_url(pkg_id),
            summary=catalog.get("description") or search_hit.get("description"),
            license=catalog.get("licenseExpression") or None,
            author=authors or None,
            homepage=catalog.get("projectUrl") or search_hit.get("projectUrl") or None,
            released=catalog.get("published"),
            first_release=first_catalog.get("published"),
            release_count=total_versions,
            dependencies=len(dep_names),
            downloads=search_hit.get("totalDownloads"),
            downloads_label="all time",
            requires=", ".join(frameworks[:3]) if frameworks else None,
            keywords=[str(t) for t in tags_raw[:10] if t],
            deprecated=deprecated_msg,
            yanked=not catalog.get("listed", True),
        )

    async def versions(self, name: str) -> VersionList:
        canonical, leaves = await self.registration(name)
        entries: list[VersionEntry] = []
        for leaf in leaves:
            cat = leaf.get("catalogEntry") or {}
            ver = str(cat.get("version") or "")
            if not ver:
                continue
            entries.append(
                VersionEntry(
                    ver,
                    cat.get("published"),
                    prerelease(ver),
                    yanked=not cat.get("listed", True),
                    deprecated=bool(cat.get("deprecation")),
                )
            )
        entries.sort(key=lambda e: version_key(e.version), reverse=True)
        latest = next((e.version for e in entries if not e.prerelease and not e.yanked), entries[0].version if entries else None)
        return VersionList(canonical, latest, entries, len(entries), NUGET.page_url(canonical))

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        canonical, leaves = await self.registration(name)
        target_leaf = leaves[-1]
        if version:
            matched = next(
                (leaf for leaf in leaves if str((leaf.get("catalogEntry") or {}).get("version") or "").casefold() == version.casefold()),
                None,
            )
            if not matched:
                msg = f"Version `{version}` of `{canonical}` was not found on NuGet."
                raise RegistryError(msg)
            target_leaf = matched

        cat = target_leaf.get("catalogEntry") or {}
        ver = str(cat.get("version") or version or "latest")
        groups: dict[str, list[str]] = {}
        frameworks: list[str] = []
        for group in cat.get("dependencyGroups") or []:
            fw = group.get("targetFramework") or "Any framework"
            if group.get("targetFramework"):
                frameworks.append(group["targetFramework"])
            deps = [
                f"{dep['id']} {dep.get('range', '')}".strip() for dep in (group.get("dependencies") or []) if isinstance(dep, dict) and dep.get("id")
            ]
            if deps:
                groups[fw] = sorted(deps, key=str.lower)

        return DependencyList(canonical, ver, groups, NUGET.page_url(canonical), ", ".join(frameworks[:3]) or None)

    async def search(self, query: str) -> SearchResult:
        data = await self.fetch.json(
            self.search_url,
            params={"q": query, "take": SEARCH_LIMIT, "prerelease": "true"},
            source="NuGet",
            missing="NuGet search is unavailable.",
        )
        hits = [
            SearchHit(
                entry["id"],
                entry.get("version"),
                entry.get("description"),
                NUGET.page_url(entry["id"]),
                None,
                f"{compact(entry['totalDownloads'])} downloads" if entry.get("totalDownloads") else None,
            )
            for entry in (data.get("data") or [])[:SEARCH_LIMIT]
            if entry.get("id")
        ]
        if not hits:
            msg = f"No NuGet packages matched {code(query)}."
            raise RegistryError(msg)
        return SearchResult(hits, data.get("totalHits"))


class PubRegistry(Registry):
    ecosystem = PUB
    base = "https://pub.dev/api"

    async def package(self, name: str) -> dict[str, Any]:
        return await self.fetch.json(
            f"{self.base}/packages/{quote(name, safe='')}",
            source="pub.dev",
            missing=f"`{name}` was not found on pub.dev.",
        )

    async def info(self, name: str) -> PackageInfo:
        data, score = await asyncio.gather(
            self.package(name),
            self.attempt(self.fetch.json(f"{self.base}/packages/{quote(name, safe='')}/score", source="pub.dev", missing="")),
        )
        latest = data.get("latest") or {}
        pubspec = latest.get("pubspec") or {}
        versions = data.get("versions") or []
        times = [v["published"] for v in versions if isinstance(v, dict) and v.get("published")]

        deps = pubspec.get("dependencies") or {}
        runtime_deps = sum(1 for k in deps if k != "flutter")
        sdk_req = (pubspec.get("environment") or {}).get("sdk")

        tags = (score or {}).get("tags") or []
        licence = next(
            (
                t.removeprefix("license:").upper()
                for t in tags
                if isinstance(t, str) and t.startswith("license:") and t not in {"license:fsf-libre", "license:osi-approved"}
            ),
            None,
        )

        facts_list: list[tuple[str, str]] = []
        if (score or {}).get("likeCount") is not None:
            facts_list.append(("Likes", f"{score['likeCount']:,}"))
        if (score or {}).get("grantedPoints") is not None and (score or {}).get("maxPoints"):
            facts_list.append(("Pub points", f"{score['grantedPoints']}/{score['maxPoints']}"))

        pkg_name = data.get("name") or name
        return PackageInfo(
            ecosystem=PUB,
            name=pkg_name,
            version=str(latest.get("version") or "unknown"),
            url=PUB.page_url(pkg_name),
            summary=pubspec.get("description"),
            license=licence,
            homepage=pubspec.get("homepage") or None,
            repository=normalize_repo(pubspec.get("repository") or pubspec.get("issue_tracker")),
            documentation=pubspec.get("documentation") or f"https://pub.dev/documentation/{pkg_name}/latest/",
            released=latest.get("published"),
            first_release=min(times, default=None),
            release_count=len(versions) or None,
            dependencies=runtime_deps,
            downloads=(score or {}).get("downloadCount30Days"),
            downloads_label="last 30 days",
            requires=sdk_req,
            keywords=[str(t) for t in (pubspec.get("topics") or [])[:10] if t],
            yanked=bool(latest.get("retracted")),
            deprecated="Discontinued on pub.dev." if "is:discontinued" in tags else None,
            facts=facts_list,
        )

    async def versions(self, name: str) -> VersionList:
        data = await self.package(name)
        pkg_name = data.get("name") or name
        latest_ver = str((data.get("latest") or {}).get("version") or "") or None
        entries = [
            VersionEntry(
                str(v["version"]),
                v.get("published"),
                prerelease(str(v["version"])),
                yanked=bool(v.get("retracted")),
            )
            for v in (data.get("versions") or [])
            if isinstance(v, dict) and v.get("version")
        ]
        entries.sort(key=lambda e: e.released or "", reverse=True)
        return VersionList(pkg_name, latest_ver, entries, len(entries), f"{PUB.page_url(pkg_name)}/versions")

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        data = await self.package(name)
        pkg_name = data.get("name") or name
        versions = data.get("versions") or []
        if version:
            target = next((v for v in versions if str(v.get("version")) == version), None)
            if not target:
                msg = f"Version `{version}` of `{pkg_name}` was not found on pub.dev."
                raise RegistryError(msg)
        else:
            target = data.get("latest") or (versions[-1] if versions else {})

        pubspec = target.get("pubspec") or {}
        groups: dict[str, list[str]] = {}
        for title, key in (("Dependencies", "dependencies"), ("Dev dependencies", "dev_dependencies")):
            raw_deps = pubspec.get(key) or {}
            if isinstance(raw_deps, dict) and raw_deps:
                formatted: list[str] = []
                for dep_name, spec in raw_deps.items():
                    if isinstance(spec, str):
                        formatted.append(f"{dep_name} {spec}".strip())
                    elif isinstance(spec, dict) and "sdk" in spec:
                        formatted.append(f"{dep_name} (sdk: {spec['sdk']})")
                    else:
                        formatted.append(dep_name)
                groups[title] = sorted(formatted, key=str.lower)

        sdk_req = (pubspec.get("environment") or {}).get("sdk")
        return DependencyList(pkg_name, str(target.get("version") or version or "latest"), groups, PUB.page_url(pkg_name), sdk_req)

    async def search(self, query: str) -> SearchResult:
        data = await self.fetch.json(
            f"{self.base}/search",
            params={"q": query},
            source="pub.dev",
            missing="pub.dev search is unavailable.",
        )
        names = [item.get("package") for item in (data.get("packages") or [])[:SEARCH_LIMIT] if isinstance(item, dict) and item.get("package")]
        if not names:
            msg = f"No Dart/Flutter packages matched {code(query)} on pub.dev."
            raise RegistryError(msg)

        details = await asyncio.gather(*(self.attempt(self.package(pkg)) for pkg in names))
        hits: list[SearchHit] = []
        for pkg_name, pkg_data in zip(names, details, strict=False):
            latest = (pkg_data or {}).get("latest") or {}
            pubspec = latest.get("pubspec") or {}
            hits.append(
                SearchHit(
                    pkg_name,
                    latest.get("version"),
                    pubspec.get("description"),
                    PUB.page_url(pkg_name),
                    latest.get("published"),
                )
            )
        return SearchResult(hits)


class HexRegistry(Registry):
    ecosystem = HEX
    base = "https://hex.pm/api"

    async def package(self, name: str) -> dict[str, Any]:
        return await self.fetch.json(
            f"{self.base}/packages/{quote(name, safe='')}",
            source="Hex.pm",
            missing=f"`{name}` was not found on Hex.pm.",
        )

    async def info(self, name: str) -> PackageInfo:
        data = await self.package(name)
        releases = data.get("releases") or []
        latest_rel = releases[0] if releases else {}
        ver = str(data.get("latest_stable_version") or data.get("latest_version") or latest_rel.get("version") or "unknown")

        rel_detail = (
            await self.attempt(
                self.fetch.json(f"{self.base}/packages/{quote(data['name'], safe='')}/releases/{quote(ver, safe='')}", source="Hex.pm", missing="")
            )
            if ver != "unknown"
            else None
        )

        meta = data.get("meta") or {}
        links = meta.get("links") or {}
        licenses = meta.get("licenses") or []
        downloads = data.get("downloads") or {}
        reqs = (rel_detail or {}).get("requirements") or {}
        retirement = (rel_detail or {}).get("retirement") or latest_rel.get("retirement")

        deprecated_msg = None
        if isinstance(retirement, dict) and retirement:
            reason = retirement.get("reason") or "retired"
            message = retirement.get("message")
            deprecated_msg = f"Retired ({reason})" + (f": {message}" if message else ".")

        facts_list: list[tuple[str, str]] = []
        if downloads.get("all"):
            facts_list.append(("All-time downloads", f"{downloads['all']:,}"))

        return PackageInfo(
            ecosystem=HEX,
            name=data["name"],
            version=ver,
            url=data.get("html_url") or HEX.page_url(data["name"]),
            summary=meta.get("description"),
            license=", ".join(licenses) if licenses else None,
            homepage=pick_url(links, ("homepage", "website", "home")),
            repository=normalize_repo(pick_url(links, ("github", "gitlab", "repository", "source"))),
            documentation=data.get("docs_html_url") or f"https://hexdocs.pm/{data['name']}/",
            released=(rel_detail or {}).get("inserted_at") or latest_rel.get("inserted_at"),
            first_release=releases[-1].get("inserted_at") if releases else None,
            release_count=len(releases) or None,
            dependencies=len(reqs) if rel_detail else None,
            downloads=downloads.get("recent") or downloads.get("week"),
            downloads_label="recent",
            requires=(rel_detail or {}).get("elixir"),
            deprecated=deprecated_msg,
            facts=facts_list,
        )

    async def versions(self, name: str) -> VersionList:
        data = await self.package(name)
        releases = data.get("releases") or []
        latest = data.get("latest_stable_version") or data.get("latest_version")
        entries = [
            VersionEntry(
                str(rel["version"]),
                rel.get("inserted_at"),
                prerelease(str(rel["version"])),
                deprecated=bool(rel.get("retirement")),
            )
            for rel in releases
            if rel.get("version")
        ]
        return VersionList(data["name"], latest, entries, len(entries), data.get("html_url") or HEX.page_url(data["name"]))

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        data = await self.package(name)
        ver = version or data.get("latest_stable_version") or data.get("latest_version")
        if not ver:
            msg = f"`{data['name']}` has no published versions on Hex.pm."
            raise RegistryError(msg)

        rel = await self.fetch.json(
            f"{self.base}/packages/{quote(data['name'], safe='')}/releases/{quote(str(ver), safe='')}",
            source="Hex.pm",
            missing=f"Version `{ver}` of `{data['name']}` was not found on Hex.pm.",
        )
        groups: dict[str, list[str]] = {}
        for dep_name, spec in (rel.get("requirements") or {}).items():
            if not isinstance(spec, dict):
                continue
            req = spec.get("requirement") or ""
            title = "Optional dependencies" if spec.get("optional") else "Dependencies"
            groups.setdefault(title, []).append(f"{dep_name} {req}".strip())

        ordered = {title: sorted(groups[title], key=str.lower) for title in ("Dependencies", "Optional dependencies") if title in groups}
        return DependencyList(data["name"], str(ver), ordered, data.get("html_url") or HEX.page_url(data["name"]), rel.get("elixir"))

    async def search(self, query: str) -> SearchResult:
        data = await self.fetch.json(
            f"{self.base}/packages",
            params={"search": query, "sort": "recent_downloads"},
            source="Hex.pm",
            missing="Hex.pm search is unavailable.",
        )
        if not isinstance(data, list) or not data:
            msg = f"No Hex packages matched {code(query)}."
            raise RegistryError(msg)

        hits: list[SearchHit] = []
        for entry in data[:SEARCH_LIMIT]:
            meta = entry.get("meta") or {}
            downloads = (entry.get("downloads") or {}).get("recent") or (entry.get("downloads") or {}).get("all")
            hits.append(
                SearchHit(
                    entry["name"],
                    entry.get("latest_stable_version") or entry.get("latest_version"),
                    meta.get("description"),
                    entry.get("html_url") or HEX.page_url(entry["name"]),
                    entry.get("updated_at"),
                    f"{compact(downloads)} downloads" if downloads else None,
                )
            )
        return SearchResult(hits, len(data))


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

    ver_display = info.version if info.version.startswith("go") else f"v{safe(info.version, 30)}"
    top = header(
        f"[{safe(info.name, 100)}]({info.url})",
        DOT.join([eco.label, ver_display, *badges]),
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
    install_cmd = eco.install.format(name=info.name, version=info.version)
    fence = "elixir" if eco is HEX else "sh"
    install = text(f"```{fence}\n{install_cmd}\n```")

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
    stamp = when(entry.released)
    if stamp:
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
    dl_note = f"Downloads cover {first.downloads_label}" + (" (from pypistats.org)" if eco is PYPI else "") + ". " if first.downloads_label else ""
    footer = f"-# {dl_note}Dependencies count direct runtime requirements only."
    return collect(
        header(f"{safe(first.name, 60)} vs {safe(second.name, 60)}", eco.label, thumbnail=eco.icon),
        discord.ui.Separator(),
        text(compare_table(first, second)),
        text("\n".join(notes)) if notes else None,
        text(footer),
    )


class Packages(commands.Cog, name="Packages"):
    """Look up, compare and search packages across PyPI, npm, crates.io, Go, Packagist, RubyGems, NuGet, pub.dev and Hex.pm."""

    help_emoji = "\N{PACKAGE}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        fetch = Fetcher(bot.http_session)
        self.registries: dict[Ecosystem, Registry] = {
            PYPI: PyPIRegistry(fetch),
            NPM: NpmRegistry(fetch),
            CRATES: CratesRegistry(fetch),
            GO: GoRegistry(fetch),
            PACKAGIST: PackagistRegistry(fetch),
            RUBYGEMS: RubyGemsRegistry(fetch),
            NUGET: NuGetRegistry(fetch),
            PUB: PubRegistry(fetch),
            HEX: HexRegistry(fetch),
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
        if info.documentation and info.documentation != info.url:
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
        """Get info about a Python package directly from PyPI."""
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

    @pypisearch.command(name="search", aliases=["find", "s"], extras={"examples": ["pypisearch search async http"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pypi_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on PyPI."),
    ) -> discord.Message:
        """Searches PyPI for packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, PYPI, query))

    @commands.group(name="npmsearch", aliases=["npm"], invoke_without_command=True, extras={"examples": ["npmsearch react", "npmsearch @types/node"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def npmsearch(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The package to search for."),
    ) -> discord.Message:
        """Get info about an npm package directly from the npm Registry."""
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

    @npmsearch.command(name="search", aliases=["find", "s"], extras={"examples": ["npmsearch search state management"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def npm_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on npm."),
    ) -> discord.Message:
        """Searches npm for packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, NPM, query))

    @commands.group(name="crate", aliases=["crates"], invoke_without_command=True, extras={"examples": ["crate serde"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def crate(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The crate to search for."),
    ) -> discord.Message:
        """Get info about a Rust crate directly from crates.io."""
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

    @crate.command(name="search", aliases=["find", "s"], extras={"examples": ["crate search async runtime"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def crate_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on crates.io."),
    ) -> discord.Message:
        """Searches crates.io for Rust crates matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, CRATES, query))

    @commands.group(
        name="gosearch",
        aliases=["gopkg", "gomod"],
        invoke_without_command=True,
        extras={"examples": ["gosearch github.com/gin-gonic/gin", "gosearch cobra"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gosearch(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Go module path or package keyword."),
    ) -> discord.Message:
        """Get info about a Go module or package from pkg.go.dev and the Go Module Proxy."""
        return await self.deliver(ctx, self.info_view(ctx, GO, package))

    @gosearch.command(
        name="versions", aliases=["version", "releases", "history"], extras={"examples": ["gosearch versions github.com/gin-gonic/gin"]}
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def go_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Go module whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a Go module, newest first."""
        return await self.deliver(ctx, self.versions_view(ctx, GO, package))

    @gosearch.command(
        name="deps",
        aliases=["dependencies", "dependency", "requires"],
        extras={"examples": ["gosearch deps github.com/gin-gonic/gin", "gosearch deps github.com/spf13/cobra 1.8.0"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def go_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Go module whose go.mod dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the direct and indirect module requirements declared in a Go module's go.mod."""
        return await self.deliver(ctx, self.dependencies_view(ctx, GO, package, version))

    @gosearch.command(name="search", aliases=["find", "s"], extras={"examples": ["gosearch search websocket"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def go_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on pkg.go.dev."),
    ) -> discord.Message:
        """Searches pkg.go.dev for Go packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, GO, query))

    @commands.group(
        name="packagist",
        aliases=["composer", "phpsearch", "phppkg"],
        invoke_without_command=True,
        extras={"examples": ["packagist laravel/framework", "packagist monolog"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def packagist(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Composer package (`vendor/package` or name)."),
    ) -> discord.Message:
        """Get info about a PHP Composer package from Packagist."""
        return await self.deliver(ctx, self.info_view(ctx, PACKAGIST, package))

    @packagist.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["packagist versions monolog/monolog"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def packagist_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The PHP package whose published versions to list."),
    ) -> discord.Message:
        """Lists the tagged releases of a PHP Composer package on Packagist."""
        return await self.deliver(ctx, self.versions_view(ctx, PACKAGIST, package))

    @packagist.command(
        name="deps",
        aliases=["dependencies", "dependency", "requires"],
        extras={"examples": ["packagist deps guzzlehttp/guzzle", "packagist deps monolog/monolog 3.7.0"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def packagist_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The PHP package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest stable release."),
    ) -> discord.Message:
        """Shows the required packages, PHP extensions, dev dependencies and suggestions of a Composer package."""
        return await self.deliver(ctx, self.dependencies_view(ctx, PACKAGIST, package, version))

    @packagist.command(name="search", aliases=["find", "s"], extras={"examples": ["packagist search http client"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def packagist_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on Packagist."),
    ) -> discord.Message:
        """Searches Packagist for PHP Composer packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, PACKAGIST, query))

    @commands.group(name="gem", aliases=["rubygems", "gemsearch"], invoke_without_command=True, extras={"examples": ["gem rails", "gem nokogiri"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gem(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Ruby gem to look up."),
    ) -> discord.Message:
        """Get info about a Ruby gem from RubyGems.org."""
        return await self.deliver(ctx, self.info_view(ctx, RUBYGEMS, package))

    @gem.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["gem versions rails"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gem_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The gem whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a Ruby gem."""
        return await self.deliver(ctx, self.versions_view(ctx, RUBYGEMS, package))

    @gem.command(name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["gem deps rails", "gem deps sinatra 4.0.0"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gem_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The gem whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the runtime and development dependencies of a Ruby gem."""
        return await self.deliver(ctx, self.dependencies_view(ctx, RUBYGEMS, package, version))

    @gem.command(name="search", aliases=["find", "s"], extras={"examples": ["gem search markdown parser"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gem_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on RubyGems."),
    ) -> discord.Message:
        """Searches RubyGems.org for gems matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, RUBYGEMS, query))

    @commands.group(
        name="nuget",
        aliases=["dotnet", "nugetsearch"],
        invoke_without_command=True,
        extras={"examples": ["nuget Newtonsoft.Json", "nuget Serilog"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def nuget(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The NuGet package ID to look up."),
    ) -> discord.Message:
        """Get info about a .NET package from NuGet.org."""
        return await self.deliver(ctx, self.info_view(ctx, NUGET, package))

    @nuget.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["nuget versions Newtonsoft.Json"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def nuget_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The NuGet package whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a NuGet package."""
        return await self.deliver(ctx, self.versions_view(ctx, NUGET, package))

    @nuget.command(name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["nuget deps Serilog"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def nuget_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The NuGet package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the target-framework dependency groups of a NuGet package."""
        return await self.deliver(ctx, self.dependencies_view(ctx, NUGET, package, version))

    @nuget.command(name="search", aliases=["find", "s"], extras={"examples": ["nuget search json serializer"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def nuget_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on NuGet."),
    ) -> discord.Message:
        """Searches NuGet.org for .NET packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, NUGET, query))

    @commands.group(
        name="pub",
        aliases=["pubdev", "pubsearch", "flutter"],
        invoke_without_command=True,
        extras={"examples": ["pub dio", "pub provider"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pub(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Dart or Flutter package to look up."),
    ) -> discord.Message:
        """Get info about a Dart or Flutter package from pub.dev."""
        return await self.deliver(ctx, self.info_view(ctx, PUB, package))

    @pub.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["pub versions dio"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pub_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The pub.dev package whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a Dart or Flutter package."""
        return await self.deliver(ctx, self.versions_view(ctx, PUB, package))

    @pub.command(name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["pub deps dio"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pub_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The pub.dev package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the dependencies and dev dependencies of a Dart or Flutter package."""
        return await self.deliver(ctx, self.dependencies_view(ctx, PUB, package, version))

    @pub.command(name="search", aliases=["find", "s"], extras={"examples": ["pub search state management"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pub_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on pub.dev."),
    ) -> discord.Message:
        """Searches pub.dev for Dart and Flutter packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, PUB, query))

    @commands.group(
        name="hex",
        aliases=["hexpm", "hexsearch"],
        invoke_without_command=True,
        extras={"examples": ["hex phoenix", "hex ecto"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def hex_command(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Elixir or Erlang package to look up."),
    ) -> discord.Message:
        """Get info about an Elixir, Erlang or Gleam package from Hex.pm."""
        return await self.deliver(ctx, self.info_view(ctx, HEX, package))

    @hex_command.command(name="versions", aliases=["version", "releases", "history"], extras={"examples": ["hex versions phoenix"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def hex_versions(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Hex package whose published versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a Hex.pm package."""
        return await self.deliver(ctx, self.versions_view(ctx, HEX, package))

    @hex_command.command(name="deps", aliases=["dependencies", "dependency"], extras={"examples": ["hex deps phoenix"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def hex_dependencies(
        self,
        ctx: commands.Context[Bot],
        package: str = commands.parameter(description="The Hex package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest stable one."),
    ) -> discord.Message:
        """Shows the dependencies of a Hex.pm package."""
        return await self.deliver(ctx, self.dependencies_view(ctx, HEX, package, version))

    @hex_command.command(name="search", aliases=["find", "s"], extras={"examples": ["hex search graphql"]})
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def hex_search(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="What to look for on Hex.pm."),
    ) -> discord.Message:
        """Searches Hex.pm for Elixir and Erlang packages matching your query."""
        return await self.deliver(ctx, self.search_view(ctx, HEX, query))

    @commands.group(name="package", aliases=["pkg"], invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package(self, ctx: commands.Context[Bot]) -> discord.Message | None:
        """Look up, compare and search packages across PyPI, npm, crates.io, Go, Packagist, RubyGems, NuGet, pub.dev and Hex.pm."""
        return await ctx.send_help(ctx.command)

    @package.command(
        name="info",
        aliases=["show", "i"],
        extras={"examples": ["package info go github.com/gin-gonic/gin", "package info php laravel/framework", "package info gem rails"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package_info(
        self,
        ctx: commands.Context[Bot],
        ecosystem: Annotated[Ecosystem, EcosystemConverter] = commands.parameter(  # noqa: B008
            converter=EcosystemConverter,
            description=f"Where the package lives: {ECOSYSTEM_NAMES}.",
        ),
        package: str = commands.parameter(description="The package name."),
    ) -> discord.Message:
        """Shows detailed metadata for a package in any supported ecosystem."""
        return await self.deliver(ctx, self.info_view(ctx, ecosystem, package))

    @package.command(
        name="versions",
        aliases=["version", "releases", "history"],
        extras={"examples": ["package versions go github.com/spf13/cobra", "package versions php monolog/monolog"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package_versions(
        self,
        ctx: commands.Context[Bot],
        ecosystem: Annotated[Ecosystem, EcosystemConverter] = commands.parameter(  # noqa: B008
            converter=EcosystemConverter,
            description=f"Where the package lives: {ECOSYSTEM_NAMES}.",
        ),
        package: str = commands.parameter(description="The package whose versions to list."),
    ) -> discord.Message:
        """Lists the published versions of a package in any supported ecosystem."""
        return await self.deliver(ctx, self.versions_view(ctx, ecosystem, package))

    @package.command(
        name="deps",
        aliases=["dependencies", "dependency", "requires"],
        extras={"examples": ["package deps go github.com/gin-gonic/gin", "package deps php guzzlehttp/guzzle"]},
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package_dependencies(
        self,
        ctx: commands.Context[Bot],
        ecosystem: Annotated[Ecosystem, EcosystemConverter] = commands.parameter(  # noqa: B008
            converter=EcosystemConverter,
            description=f"Where the package lives: {ECOSYSTEM_NAMES}.",
        ),
        package: str = commands.parameter(description="The package whose dependencies to show."),
        version: str | None = commands.parameter(default=None, description="A specific version. Defaults to the latest."),
    ) -> discord.Message:
        """Shows the declared dependencies of a package in any supported ecosystem."""
        return await self.deliver(ctx, self.dependencies_view(ctx, ecosystem, package, version))

    @package.command(
        name="compare",
        aliases=["vs", "diff"],
        extras={
            "examples": [
                "package compare pypi requests httpx",
                "package compare go github.com/gin-gonic/gin github.com/labstack/echo",
                "package compare php guzzlehttp/guzzle symfony/http-client",
            ]
        },
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package_compare(
        self,
        ctx: commands.Context[Bot],
        ecosystem: Annotated[Ecosystem, EcosystemConverter] = commands.parameter(  # noqa: B008
            converter=EcosystemConverter,
            description=f"Where the packages live: {ECOSYSTEM_NAMES}.",
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
        extras={
            "examples": [
                "package search pypi http client",
                "package search go router",
                "package search phpjwt",
                "package search crates async runtime",
            ]
        },
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def package_search(
        self,
        ctx: commands.Context[Bot],
        ecosystem: Annotated[Ecosystem, EcosystemConverter] = commands.parameter(  # noqa: B008
            converter=EcosystemConverter,
            description=f"Where to search: {ECOSYSTEM_NAMES}.",
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
