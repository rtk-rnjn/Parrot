from __future__ import annotations

import asyncio
import re
from email.utils import parseaddr
from typing import Any
from urllib.parse import quote

from bs4 import BeautifulSoup
from packaging.requirements import InvalidRequirement, Requirement

from core.utils import code

from .constants import EXTRA_MARKER, REPO_HOSTS, SEARCH_LIMIT
from .ecosystem import PYPI
from .utils import (
    DependencyList,
    PackageInfo,
    Registry,
    RegistryError,
    SearchHit,
    SearchResult,
    VersionEntry,
    VersionList,
    pick_url,
    prerelease,
    truncate,
    version_key,
)


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
