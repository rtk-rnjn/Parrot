from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote

from core.utils import code

from .constants import SEARCH_LIMIT
from .ecosystem import NUGET
from .utils import (
    DependencyList,
    PackageInfo,
    Registry,
    RegistryError,
    SearchHit,
    SearchResult,
    VersionEntry,
    VersionList,
    compact,
    prerelease,
    version_key,
)


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
