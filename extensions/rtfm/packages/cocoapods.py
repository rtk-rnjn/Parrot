from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import quote

from core.utils import code

from .constants import DOT, SEARCH_LIMIT
from .ecosystem import COCOAPODS
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
    prerelease,
    version_key,
)


class CocoaPodsRegistry(Registry):
    ecosystem = COCOAPODS
    trunk_base = "https://trunk.cocoapods.org/api/v1/pods"
    cdn_base = "https://cdn.cocoapods.org/Specs"
    search_url = "https://search.cocoapods.org/api/v1/pods.picky.hash.json"

    @staticmethod
    def shard_prefix(pod_name: str) -> str:
        digest = hashlib.md5(pod_name.encode("utf-8")).hexdigest()  # noqa: S324
        return f"{digest[0]}/{digest[1]}/{digest[2]}"

    async def trunk_pod(self, name: str) -> dict[str, Any]:
        cleaned = name.strip()
        return await self.fetch.json(
            f"{self.trunk_base}/{quote(cleaned, safe='')}",
            source="CocoaPods",
            missing=f"`{cleaned}` was not found on CocoaPods.",
        )

    async def podspec(self, pod_name: str, version: str) -> dict[str, Any]:
        shard = self.shard_prefix(pod_name)
        url = f"{self.cdn_base}/{shard}/{quote(pod_name, safe='')}/{quote(version, safe='')}/{quote(pod_name, safe='')}.podspec.json"
        return await self.fetch.json(
            url,
            source="CocoaPods CDN",
            missing=f"Podspec for `{pod_name}` ({version}) was not found on CocoaPods.",
        )

    @staticmethod
    def collect_dependencies(spec: dict[str, Any]) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}

        def _format_deps(dep_dict: dict[str, Any]) -> list[str]:
            items: list[str] = []
            for dep_name, constraints in dep_dict.items():
                if isinstance(constraints, list) and constraints:
                    items.append(f"{dep_name} ({', '.join(str(c) for c in constraints)})")
                elif isinstance(constraints, str) and constraints:
                    items.append(f"{dep_name} ({constraints})")
                else:
                    items.append(dep_name)
            return sorted(items, key=str.lower)

        if isinstance(spec.get("dependencies"), dict) and spec["dependencies"]:
            groups["Pod dependencies"] = _format_deps(spec["dependencies"])

        for sub in spec.get("subspecs") or []:
            if isinstance(sub, dict) and isinstance(sub.get("dependencies"), dict) and sub["dependencies"]:
                sub_name = sub.get("name") or "Subspec"
                groups[f"Subspec: {sub_name}"] = _format_deps(sub["dependencies"])

        frameworks = spec.get("frameworks")
        if isinstance(frameworks, list) and frameworks:
            groups["System Frameworks"] = sorted([str(f) for f in frameworks], key=str.lower)
        elif isinstance(frameworks, str) and frameworks:
            groups["System Frameworks"] = [frameworks]

        return groups

    async def info(self, name: str) -> PackageInfo:
        trunk = await self.trunk_pod(name)
        versions_raw = trunk.get("versions") or []
        if not versions_raw:
            msg = f"`{name}` has no published versions on CocoaPods."
            raise RegistryError(msg)

        versions_sorted = sorted(
            versions_raw,
            key=lambda v: version_key(str(v.get("name") or "")),
            reverse=True,
        )
        stable_versions = [v for v in versions_sorted if not prerelease(str(v.get("name") or ""))]
        latest_entry = stable_versions[0] if stable_versions else versions_sorted[0]
        latest_ver = str(latest_entry.get("name") or "unknown")

        created_times = [v["created_at"] for v in versions_raw if v.get("created_at")]
        canonical_from_spec = name.strip()
        spec = await self.attempt(self.podspec(canonical_from_spec, latest_ver)) or {}

        pod_name = str(spec.get("name") or canonical_from_spec)
        lic_raw = spec.get("license")
        licence = lic_raw.get("type") if isinstance(lic_raw, dict) else (str(lic_raw) if lic_raw else None)

        authors_raw = spec.get("authors") or spec.get("author")
        if isinstance(authors_raw, dict):
            author_str = ", ".join(str(k) for k in list(authors_raw.keys())[:4])
        elif isinstance(authors_raw, list):
            author_str = ", ".join(str(a) for a in authors_raw[:4])
        elif isinstance(authors_raw, str):
            author_str = authors_raw
        else:
            author_str = None

        source_info = spec.get("source") or {}
        repo_url = normalize_repo(source_info.get("git") or source_info.get("http"))

        platforms = spec.get("platforms") or {}
        plat_parts = [f"{k} {v}" if v else str(k) for k, v in platforms.items()] if isinstance(platforms, dict) else []

        dep_groups = self.collect_dependencies(spec)
        direct_deps = len(dep_groups.get("Pod dependencies", []))

        swift_vers = spec.get("swift_versions") or spec.get("swift_version")
        if isinstance(swift_vers, list):
            swift_str = ", ".join(str(s) for s in swift_vers[:4])
        elif swift_vers:
            swift_str = str(swift_vers)
        else:
            swift_str = None

        facts_list: list[tuple[str, str]] = []
        if swift_str:
            facts_list.append(("Swift versions", f"`{swift_str}`"))
        if spec.get("cocoapods_version"):
            facts_list.append(("CocoaPods requirement", f"`{spec['cocoapods_version']}`"))

        deprecated_msg = None
        if spec.get("deprecated_in_favor_of"):
            deprecated_msg = f"Deprecated in favor of `{spec['deprecated_in_favor_of']}`."
        elif spec.get("deprecated"):
            deprecated_msg = "This pod is marked as deprecated."

        return PackageInfo(
            ecosystem=COCOAPODS,
            name=pod_name,
            version=latest_ver,
            url=COCOAPODS.page_url(pod_name),
            summary=spec.get("summary") or spec.get("description"),
            license=licence,
            author=author_str,
            homepage=spec.get("homepage"),
            repository=repo_url,
            documentation=spec.get("documentation_url"),
            released=latest_entry.get("created_at"),
            first_release=min(created_times, default=None),
            release_count=len(versions_raw),
            dependencies=direct_deps,
            requires=", ".join(plat_parts) if plat_parts else None,
            deprecated=deprecated_msg,
            facts=facts_list,
        )

    async def versions(self, name: str) -> VersionList:
        trunk = await self.trunk_pod(name)
        versions_raw = trunk.get("versions") or []
        entries = [
            VersionEntry(
                str(v["name"]),
                v.get("created_at"),
                prerelease(str(v["name"])),
            )
            for v in versions_raw
            if v.get("name")
        ]
        entries.sort(key=lambda e: version_key(e.version), reverse=True)
        latest = next((e.version for e in entries if not e.prerelease), entries[0].version if entries else None)
        return VersionList(name.strip(), latest, entries, len(entries), COCOAPODS.page_url(name.strip()))

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        trunk = await self.trunk_pod(name)
        versions_raw = trunk.get("versions") or []
        if not version:
            versions_sorted = sorted(versions_raw, key=lambda v: version_key(str(v.get("name") or "")), reverse=True)
            stable = [v for v in versions_sorted if not prerelease(str(v.get("name") or ""))]
            version = str((stable[0] if stable else versions_sorted[0]).get("name"))

        spec = await self.podspec(name.strip(), version)
        pod_name = str(spec.get("name") or name.strip())
        groups = self.collect_dependencies(spec)
        platforms = spec.get("platforms") or {}
        plat_parts = [f"{k} {v}" if v else str(k) for k, v in platforms.items()] if isinstance(platforms, dict) else []
        return DependencyList(pod_name, version, groups, COCOAPODS.page_url(pod_name), ", ".join(plat_parts) or None)

    async def search(self, query: str) -> SearchResult:
        data = await self.attempt(
            self.fetch.json(
                self.search_url,
                params={"query": query, "ids": SEARCH_LIMIT},
                source="CocoaPods",
                missing="CocoaPods search is unavailable.",
            )
        )
        allocations = ((data or {}).get("allocations")) or []
        hits: list[SearchHit] = []
        for alloc in allocations:
            if not isinstance(alloc, list) or len(alloc) < 6 or not isinstance(alloc[5], list):
                continue
            for item in alloc[5]:
                if not isinstance(item, dict) or not item.get("id"):
                    continue
                pod_id = str(item["id"])
                platforms = item.get("platforms") or []
                details = []
                if isinstance(platforms, list) and platforms:
                    details.append(", ".join(str(p) for p in platforms[:4]))
                hits.append(
                    SearchHit(
                        pod_id,
                        str(item.get("version")) if item.get("version") else None,
                        item.get("summary"),
                        item.get("link") or COCOAPODS.page_url(pod_id),
                        None,
                        DOT.join(details) or None,
                    )
                )
                if len(hits) >= SEARCH_LIMIT:
                    break
            if len(hits) >= SEARCH_LIMIT:
                break

        if not hits and COCOAPODS.name_pattern.fullmatch(query.strip()):
            info = await self.attempt(self.info(query.strip()))
            if info:
                return SearchResult([SearchHit(info.name, info.version, info.summary, info.url, info.released)])

        if not hits:
            msg = f"No pods matched {code(query)} on CocoaPods."
            raise RegistryError(msg)
        return SearchResult(hits, (data or {}).get("total"))
