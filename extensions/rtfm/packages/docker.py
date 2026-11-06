from __future__ import annotations

from typing import Any
from urllib.parse import quote

from core.utils import code, file_size

from .constants import DOT, SEARCH_LIMIT
from .ecosystem import DOCKER
from .utils import DependencyList, PackageInfo, Registry, RegistryError, SearchHit, SearchResult, VersionEntry, VersionList, compact, prerelease


class DockerHubRegistry(Registry):
    ecosystem = DOCKER
    hub_base = "https://hub.docker.com/v2"

    @staticmethod
    def split_repo(name: str) -> tuple[str, str, str]:
        cleaned = name.strip().strip("/").lower()
        if "/" in cleaned:
            namespace, repo = cleaned.split("/", 1)
            display = f"{namespace}/{repo}"
        else:
            namespace, repo = "library", cleaned
            display = cleaned
        return namespace, repo, display

    @staticmethod
    def hub_url(namespace: str, repo: str) -> str:
        if namespace == "library":
            return f"https://hub.docker.com/_/{quote(repo, safe='')}"
        return f"https://hub.docker.com/r/{quote(namespace, safe='')}/{quote(repo, safe='')}"

    async def repository_data(self, name: str) -> tuple[str, str, str, dict[str, Any]]:
        namespace, repo, display = self.split_repo(name)
        data = await self.fetch.json(
            f"{self.hub_base}/repositories/{quote(namespace, safe='')}/{quote(repo, safe='')}/",
            source="Docker Hub",
            missing=f"`{display}` was not found on Docker Hub.",
        )
        return namespace, repo, display, data

    async def tags_data(self, namespace: str, repo: str, display: str, page_size: int = 50) -> dict[str, Any]:
        return await self.fetch.json(
            f"{self.hub_base}/repositories/{quote(namespace, safe='')}/{quote(repo, safe='')}/tags/",
            params={"page_size": page_size},
            source="Docker Hub",
            missing=f"`{display}` has no tags on Docker Hub.",
        )

    async def info(self, name: str) -> PackageInfo:
        namespace, repo, display, data = await self.repository_data(name)
        tags_resp = await self.attempt(self.tags_data(namespace, repo, display, page_size=25))
        tags = (tags_resp or {}).get("results") or []
        total_tags = (tags_resp or {}).get("count") or len(tags) or None

        chosen_tag = next((t for t in tags if t.get("name") == "latest"), tags[0] if tags else {})
        tag_name = str(chosen_tag.get("name") or "latest")
        size = chosen_tag.get("full_size")

        images = chosen_tag.get("images") or []
        archs = sorted({f"{img.get('os', 'linux')}/{img.get('architecture')}" for img in images if img.get("architecture")})

        facts_list: list[tuple[str, str]] = [("Namespace", f"`{namespace}`")]
        if data.get("star_count") is not None:
            facts_list.append(("Stars", f"{data['star_count']:,}"))
        if namespace == "library":
            facts_list.append(("Official Image", "Yes \N{WHITE HEAVY CHECK MARK}"))

        return PackageInfo(
            ecosystem=DOCKER,
            name=display,
            version=tag_name,
            url=self.hub_url(namespace, repo),
            summary=data.get("description"),
            author=namespace if namespace != "library" else "Docker Official Images",
            released=chosen_tag.get("last_updated") or data.get("last_updated"),
            first_release=data.get("date_registered"),
            release_count=total_tags,
            downloads=data.get("pull_count"),
            downloads_label="total pulls",
            size=size,
            requires=", ".join(archs[:4]) if archs else None,
            keywords=[str(c.get("name")) for c in (data.get("categories") or []) if isinstance(c, dict) and c.get("name")],
            facts=facts_list,
        )

    async def versions(self, name: str) -> VersionList:
        namespace, repo, display = self.split_repo(name)
        tags_resp = await self.tags_data(namespace, repo, display, page_size=100)
        results = tags_resp.get("results") or []
        total = tags_resp.get("count") or len(results)

        entries: list[VersionEntry] = []
        for tag in results:
            tname = str(tag.get("name") or "")
            if not tname:
                continue
            fsize = tag.get("full_size")
            images = tag.get("images") or []
            archs = sorted({img.get("architecture") for img in images if img.get("architecture")})
            notes = []
            if fsize:
                notes.append(file_size(fsize))
            if archs:
                notes.append(", ".join(archs[:3]))
            entries.append(
                VersionEntry(
                    tname,
                    tag.get("last_updated"),
                    prerelease(tname) and tname != "latest",
                    note=DOT.join(notes) or None,
                )
            )

        latest = next((e.version for e in entries if e.version == "latest"), entries[0].version if entries else None)
        return VersionList(display, latest, entries, total, f"{self.hub_url(namespace, repo)}/tags")

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        namespace, repo, display = self.split_repo(name)
        tag_to_fetch = version or "latest"
        tag_data = await self.attempt(
            self.fetch.json(
                f"{self.hub_base}/repositories/{quote(namespace, safe='')}/{quote(repo, safe='')}/tags/{quote(tag_to_fetch, safe='')}/",
                source="Docker Hub",
                missing="",
            )
        )
        if not tag_data:
            tags_resp = await self.tags_data(namespace, repo, display, page_size=5)
            results = tags_resp.get("results") or []
            if not results:
                msg = f"Tag `{tag_to_fetch}` of `{display}` was not found on Docker Hub."
                raise RegistryError(msg)
            tag_data = results[0]
            tag_to_fetch = str(tag_data.get("name") or tag_to_fetch)

        groups: dict[str, list[str]] = {}
        os_set: set[str] = set()
        for img in tag_data.get("images") or []:
            os_name = img.get("os") or "linux"
            arch = img.get("architecture") or "unknown"
            variant = f"/{img['variant']}" if img.get("variant") else ""
            size_str = f" ({file_size(img['size'])})" if img.get("size") else ""
            digest = (img.get("digest") or "")[:19]
            os_set.add(os_name)
            label = f"{os_name}/{arch}{variant}{size_str}" + (f" [{digest}]" if digest else "")
            groups.setdefault(f"Platform: {os_name}", []).append(label)

        return DependencyList(
            display,
            tag_to_fetch,
            groups,
            f"{self.hub_url(namespace, repo)}/tags",
            ", ".join(sorted(os_set)) if os_set else None,
        )

    async def search(self, query: str) -> SearchResult:
        data = await self.fetch.json(
            f"{self.hub_base}/search/repositories/",
            params={"query": query, "page_size": SEARCH_LIMIT},
            source="Docker Hub",
            missing="Docker Hub search is unavailable.",
        )
        hits: list[SearchHit] = []
        for entry in (data.get("results") or [])[:SEARCH_LIMIT]:
            repo_name = entry.get("repo_name")
            if not repo_name:
                continue
            namespace, repo, _ = self.split_repo(repo_name)
            details = []
            if entry.get("pull_count") is not None:
                details.append(f"{compact(entry['pull_count'])} pulls")
            if entry.get("star_count"):
                details.append(f"\N{BLACK STAR} {compact(entry['star_count'])}")
            if entry.get("is_official"):
                details.append("official")
            hits.append(
                SearchHit(
                    repo_name,
                    None,
                    entry.get("short_description"),
                    self.hub_url(namespace, repo),
                    None,
                    DOT.join(details) or None,
                )
            )
        if not hits:
            msg = f"No container images matched {code(query)} on Docker Hub."
            raise RegistryError(msg)
        return SearchResult(hits, data.get("count"))
