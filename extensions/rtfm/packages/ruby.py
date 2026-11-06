from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote

from core.utils import code

from .constants import SEARCH_LIMIT
from .ecosystem import RUBYGEMS
from .utils import DependencyList, PackageInfo, Registry, RegistryError, SearchHit, SearchResult, VersionEntry, VersionList, compact, normalize_repo


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
