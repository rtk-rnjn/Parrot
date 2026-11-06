from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import quote, urlparse

from bs4 import BeautifulSoup

from core.utils import code

from .constants import DOT, SEARCH_LIMIT
from .ecosystem import SWIFT
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

PACKAGE_DEP_RE = re.compile(
    r'\.package\s*\(\s*(?:name\s*:\s*"[^"]*"\s*,\s*)?url\s*:\s*"([^"]+)"\s*(?:,\s*([^)]+))?\)',
    re.DOTALL,
)
PLATFORMS_BLOCK_RE = re.compile(r"platforms\s*:\s*\[(.*?)\]", re.DOTALL)
PLATFORM_ITEM_RE = re.compile(r"\.(iOS|macOS|tvOS|watchOS|visionOS|macCatalyst)\s*\(\s*\.?([^)]+)\)")
SWIFT_TOOLS_RE = re.compile(r"//\s*swift-tools-version\s*:\s*([0-9.]+)")


class SwiftRegistry(Registry):
    ecosystem = SWIFT
    spi_base = "https://swiftpackageindex.com"
    gh_api = "https://api.github.com"

    async def resolve_owner_repo(self, name: str) -> tuple[str, str]:
        cleaned = name.strip().strip("/")
        if "/" in cleaned:
            owner, repo = cleaned.split("/", 1)
            return owner, repo.removesuffix(".git")

        search_res = await self.attempt(self.search(cleaned))
        if search_res and search_res.hits:
            first_name = search_res.hits[0].name
            if "/" in first_name:
                owner, repo = first_name.split("/", 1)
                return owner, repo

        gh_search = await self.attempt(
            self.fetch.json(
                f"{self.gh_api}/search/repositories",
                params={"q": f"{cleaned} language:Swift", "per_page": 1},
                source="GitHub",
                missing="",
            )
        )
        items = (gh_search or {}).get("items") or []
        if items and items[0].get("full_name"):
            owner, repo = str(items[0]["full_name"]).split("/", 1)
            return owner, repo

        msg = f"`{name}` was not found on the Swift Package Index. Use `owner/repo` (e.g. `Alamofire/Alamofire`)."
        raise RegistryError(msg)

    async def fetch_tags(self, owner: str, repo: str) -> list[dict[str, Any]]:
        data = await self.attempt(
            self.fetch.json(
                f"{self.gh_api}/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/tags",
                params={"per_page": 100},
                source="GitHub",
                missing="",
            )
        )
        return data if isinstance(data, list) else []

    async def fetch_releases(self, owner: str, repo: str) -> list[dict[str, Any]]:
        data = await self.attempt(
            self.fetch.json(
                f"{self.gh_api}/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/releases",
                params={"per_page": 50},
                source="GitHub",
                missing="",
            )
        )
        return data if isinstance(data, list) else []

    async def fetch_package_swift(self, owner: str, repo: str, ref: str) -> str | None:
        url = f"https://raw.githubusercontent.com/{quote(owner, safe='')}/{quote(repo, safe='')}/{quote(ref, safe='')}/Package.swift"
        return await self.attempt(self.fetch.text(url, source="GitHub", missing=""))

    @staticmethod
    def parse_package_swift(content: str | None) -> tuple[str | None, list[str], list[str]]:
        if not content:
            return None, [], []
        tools_match = SWIFT_TOOLS_RE.search(content)
        tools_ver = tools_match.group(1) if tools_match else None

        platforms: list[str] = []
        plat_block = PLATFORMS_BLOCK_RE.search(content)
        if plat_block:
            for m in PLATFORM_ITEM_RE.finditer(plat_block.group(1)):
                ver_clean = m.group(2).strip().strip('"').replace("_", ".")
                platforms.append(f"{m.group(1)} {ver_clean}")

        deps: list[str] = []
        for match in PACKAGE_DEP_RE.finditer(content):
            raw_url = match.group(1).strip()
            constraint_raw = (match.group(2) or "").strip()
            parsed = urlparse(raw_url)
            slug = parsed.path.strip("/").removesuffix(".git") if parsed.netloc else raw_url
            constraint_clean = re.sub(r"\s+", " ", constraint_raw.replace('"', ""))
            deps.append(f"{slug} ({constraint_clean})" if constraint_clean else slug)

        return tools_ver, platforms, deps

    async def info(self, name: str) -> PackageInfo:
        owner, repo = await self.resolve_owner_repo(name)
        full_name = f"{owner}/{repo}"
        repo_data, releases, tags = await asyncio.gather(
            self.fetch.json(
                f"{self.gh_api}/repos/{quote(owner, safe='')}/{quote(repo, safe='')}",
                source="Swift Package Index / GitHub",
                missing=f"`{full_name}` was not found.",
            ),
            self.fetch_releases(owner, repo),
            self.fetch_tags(owner, repo),
        )

        default_branch = repo_data.get("default_branch") or "main"
        latest_ver = (
            str(releases[0]["tag_name"]).removeprefix("v")
            if releases and releases[0].get("tag_name")
            else (str(tags[0]["name"]).removeprefix("v") if tags and tags[0].get("name") else default_branch)
        )
        ref_to_read = (
            str(releases[0]["tag_name"])
            if releases and releases[0].get("tag_name")
            else (str(tags[0]["name"]) if tags and tags[0].get("name") else default_branch)
        )

        pkg_swift = await self.fetch_package_swift(owner, repo, ref_to_read)
        if pkg_swift is None and ref_to_read != default_branch:
            pkg_swift = await self.fetch_package_swift(owner, repo, default_branch)

        tools_ver, platforms, deps = self.parse_package_swift(pkg_swift)
        rel_dates = [r["published_at"] for r in releases if r.get("published_at")]

        lic = (repo_data.get("license") or {}).get("spdx_id")
        if lic == "NOASSERTION":
            lic = (repo_data.get("license") or {}).get("name")

        req_parts = []
        if tools_ver:
            req_parts.append(f"Swift {tools_ver}+")
        if platforms:
            req_parts.append(", ".join(platforms[:3]))

        facts_list: list[tuple[str, str]] = []
        if repo_data.get("stargazers_count") is not None:
            facts_list.append(("Stars", f"{repo_data['stargazers_count']:,}"))
        if repo_data.get("forks_count") is not None:
            facts_list.append(("Forks", f"{repo_data['forks_count']:,}"))

        deprecated_msg = "This repository is archived." if repo_data.get("archived") else None

        return PackageInfo(
            ecosystem=SWIFT,
            name=full_name,
            version=latest_ver,
            url=SWIFT.page_url(full_name),
            summary=repo_data.get("description"),
            license=lic,
            author=(repo_data.get("owner") or {}).get("login") or owner,
            homepage=repo_data.get("homepage") or None,
            repository=repo_data.get("html_url"),
            released=rel_dates[0] if rel_dates else repo_data.get("pushed_at"),
            first_release=min(rel_dates, default=repo_data.get("created_at")),
            release_count=len(tags) or len(releases) or None,
            dependencies=len(deps),
            requires=" / ".join(req_parts) if req_parts else None,
            keywords=[str(t) for t in (repo_data.get("topics") or [])[:10] if t],
            deprecated=deprecated_msg,
            facts=facts_list,
        )

    async def versions(self, name: str) -> VersionList:
        owner, repo = await self.resolve_owner_repo(name)
        full_name = f"{owner}/{repo}"
        releases, tags = await asyncio.gather(self.fetch_releases(owner, repo), self.fetch_tags(owner, repo))

        rel_map = {str(r.get("tag_name") or "").removeprefix("v"): r for r in releases if r.get("tag_name")}
        seen: set[str] = set()
        entries: list[VersionEntry] = []

        for r in releases:
            raw_tag = str(r.get("tag_name") or "")
            ver = raw_tag.removeprefix("v")
            if not ver or ver in seen:
                continue
            seen.add(ver)
            entries.append(
                VersionEntry(
                    ver,
                    r.get("published_at"),
                    bool(r.get("prerelease")) or prerelease(ver),
                )
            )

        for t in tags:
            raw_tag = str(t.get("name") or "")
            ver = raw_tag.removeprefix("v")
            if not ver or ver in seen:
                continue
            seen.add(ver)
            rel = rel_map.get(ver)
            entries.append(
                VersionEntry(
                    ver,
                    rel.get("published_at") if rel else None,
                    prerelease(ver),
                )
            )

        entries.sort(key=lambda e: version_key(e.version), reverse=True)
        latest = next((e.version for e in entries if not e.prerelease), entries[0].version if entries else None)
        return VersionList(full_name, latest, entries, len(entries), SWIFT.page_url(full_name))

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        owner, repo = await self.resolve_owner_repo(name)
        full_name = f"{owner}/{repo}"

        pkg_swift = None
        if version:
            for candidate in (f"v{version}", version):
                pkg_swift = await self.fetch_package_swift(owner, repo, candidate)
                if pkg_swift is not None:
                    break
            if pkg_swift is None:
                msg = f"Could not find `Package.swift` for version `{version}` of `{full_name}`."
                raise RegistryError(msg)
            resolved_ver = version
        else:
            repo_data = await self.fetch.json(
                f"{self.gh_api}/repos/{quote(owner, safe='')}/{quote(repo, safe='')}",
                source="GitHub",
                missing=f"`{full_name}` was not found.",
            )
            default_branch = repo_data.get("default_branch") or "main"
            pkg_swift = await self.fetch_package_swift(owner, repo, default_branch)
            resolved_ver = default_branch

        tools_ver, platforms, deps = self.parse_package_swift(pkg_swift)
        groups: dict[str, list[str]] = {}
        if deps:
            groups["Package dependencies"] = sorted(deps, key=str.lower)
        if platforms:
            groups["Supported Platforms"] = platforms

        return DependencyList(
            full_name,
            resolved_ver,
            groups,
            SWIFT.page_url(full_name),
            f"Swift tools {tools_ver}" if tools_ver else None,
        )

    async def search(self, query: str) -> SearchResult:
        html = await self.attempt(
            self.fetch.text(
                f"{self.spi_base}/search",
                params={"query": query},
                headers={"Accept": "text/html"},
                source="Swift Package Index",
                missing="",
            )
        )
        hits: list[SearchHit] = []
        if html:
            soup = await asyncio.to_thread(BeautifulSoup, html, "html.parser")
            for a_tag in soup.select("ul#package-list li a, section.search-results li a"):
                href = str(a_tag.get("href") or "").strip("/")
                if href.count("/") != 1 or href.startswith(("search", "blog", "faq", "stylesheets", "images")):
                    continue
                h4 = a_tag.find(["h4", "strong"])
                p_tag = a_tag.find("p")
                desc = (
                    p_tag.get_text(strip=True)
                    if p_tag
                    else (h4.find_next_sibling("p").get_text(strip=True) if h4 and h4.find_next_sibling("p") else None)
                )
                hits.append(
                    SearchHit(
                        href,
                        None,
                        desc,
                        SWIFT.page_url(href),
                    )
                )
                if len(hits) >= SEARCH_LIMIT:
                    break

        if not hits:
            gh_data = await self.fetch.json(
                f"{self.gh_api}/search/repositories",
                params={"q": f"{query} language:Swift", "per_page": SEARCH_LIMIT},
                source="Swift Package Index / GitHub",
                missing="Swift package search is unavailable.",
            )
            for item in (gh_data.get("items") or [])[:SEARCH_LIMIT]:
                full_name = item.get("full_name")
                if not full_name:
                    continue
                details = []
                if item.get("stargazers_count"):
                    details.append(f"\N{BLACK STAR} {compact(item['stargazers_count'])}")
                if item.get("license") and isinstance(item["license"], dict) and item["license"].get("spdx_id"):
                    details.append(str(item["license"]["spdx_id"]))
                hits.append(
                    SearchHit(
                        full_name,
                        None,
                        item.get("description"),
                        SWIFT.page_url(full_name),
                        item.get("pushed_at"),
                        DOT.join(details) or None,
                    )
                )

        if not hits:
            msg = f"No Swift packages matched {code(query)}."
            raise RegistryError(msg)
        return SearchResult(hits)
