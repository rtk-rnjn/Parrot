from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import quote

from bs4 import BeautifulSoup

from core.utils import code

from .constants import DOT, GO_MOD_DIRECTIVE, GO_REQUIRE_BLOCK, GO_REQUIRE_SINGLE, SEARCH_LIMIT, VERSIONS_PER_PAGE
from .ecosystem import GO
from .utils import DependencyList, PackageInfo, Registry, RegistryError, SearchHit, SearchResult, VersionEntry, VersionList, prerelease, version_key


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
            if synopsis and str(synopsis).startswith("Package ") and " - Go Packages" in synopsis:
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
