from __future__ import annotations

from typing import Any
from urllib.parse import quote

from core.utils import code

from .constants import SEARCH_LIMIT
from .ecosystem import CRATES
from .utils import DependencyList, PackageInfo, Registry, RegistryError, SearchHit, SearchResult, VersionEntry, VersionList, compact


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
