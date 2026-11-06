from __future__ import annotations

import abc
import asyncio
import json
import re
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

import aiohttp
import discord
from packaging.version import InvalidVersion, Version

from core.utils import BaseLayoutView, code, dated, file_size, parse_time, safe, truncate, valid_url, when

from .constants import DEFAULT_HEADERS, DEPENDENCY_BUDGET, DOT, GROUP_BUDGET, MAX_GROUPS, MAX_RESPONSE, SEARCH_LIMIT, TIMEOUT, VERSION_PATTERN
from .ecosystem import COCOAPODS, HEX, MAVEN, PACKAGIST, PYPI, SWIFT

if TYPE_CHECKING:
    from .ecosystem import Ecosystem


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
    fence = "elixir" if eco is HEX else "kotlin" if eco is MAVEN else "ruby" if eco is COCOAPODS else "swift" if eco is SWIFT else "sh"
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
