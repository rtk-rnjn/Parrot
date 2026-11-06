from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote

from core.utils import code

from .constants import MAX_PACKUMENT, SEARCH_LIMIT
from .ecosystem import NPM
from .utils import (
    DependencyList,
    PackageInfo,
    Registry,
    RegistryError,
    SearchHit,
    SearchResult,
    VersionEntry,
    VersionList,
    normalize_repo,
    person,
    prerelease,
)


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
