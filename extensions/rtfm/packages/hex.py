from __future__ import annotations

from typing import Any
from urllib.parse import quote

from core.utils import code

from .constants import SEARCH_LIMIT
from .ecosystem import HEX
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
    normalize_repo,
    pick_url,
    prerelease,
)


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
