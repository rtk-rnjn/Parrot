from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote

from core.utils import code

from .constants import SEARCH_LIMIT
from .ecosystem import PUB
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
)


class PubRegistry(Registry):
    ecosystem = PUB
    base = "https://pub.dev/api"

    async def package(self, name: str) -> dict[str, Any]:
        return await self.fetch.json(
            f"{self.base}/packages/{quote(name, safe='')}",
            source="pub.dev",
            missing=f"`{name}` was not found on pub.dev.",
        )

    async def info(self, name: str) -> PackageInfo:
        data, score = await asyncio.gather(
            self.package(name),
            self.attempt(self.fetch.json(f"{self.base}/packages/{quote(name, safe='')}/score", source="pub.dev", missing="")),
        )
        latest = data.get("latest") or {}
        pubspec = latest.get("pubspec") or {}
        versions = data.get("versions") or []
        times = [v["published"] for v in versions if isinstance(v, dict) and v.get("published")]

        deps = pubspec.get("dependencies") or {}
        runtime_deps = sum(1 for k in deps if k != "flutter")
        sdk_req = (pubspec.get("environment") or {}).get("sdk")

        tags = (score or {}).get("tags") or []
        licence = next(
            (
                t.removeprefix("license:").upper()
                for t in tags
                if isinstance(t, str) and t.startswith("license:") and t not in {"license:fsf-libre", "license:osi-approved"}
            ),
            None,
        )

        facts_list: list[tuple[str, str]] = []
        if (score or {}).get("likeCount") is not None:
            facts_list.append(("Likes", f"{score['likeCount']:,}"))
        if (score or {}).get("grantedPoints") is not None and (score or {}).get("maxPoints"):
            facts_list.append(("Pub points", f"{score['grantedPoints']}/{score['maxPoints']}"))

        pkg_name = data.get("name") or name
        return PackageInfo(
            ecosystem=PUB,
            name=pkg_name,
            version=str(latest.get("version") or "unknown"),
            url=PUB.page_url(pkg_name),
            summary=pubspec.get("description"),
            license=licence,
            homepage=pubspec.get("homepage") or None,
            repository=normalize_repo(pubspec.get("repository") or pubspec.get("issue_tracker")),
            documentation=pubspec.get("documentation") or f"https://pub.dev/documentation/{pkg_name}/latest/",
            released=latest.get("published"),
            first_release=min(times, default=None),
            release_count=len(versions) or None,
            dependencies=runtime_deps,
            downloads=(score or {}).get("downloadCount30Days"),
            downloads_label="last 30 days",
            requires=sdk_req,
            keywords=[str(t) for t in (pubspec.get("topics") or [])[:10] if t],
            yanked=bool(latest.get("retracted")),
            deprecated="Discontinued on pub.dev." if "is:discontinued" in tags else None,
            facts=facts_list,
        )

    async def versions(self, name: str) -> VersionList:
        data = await self.package(name)
        pkg_name = data.get("name") or name
        latest_ver = str((data.get("latest") or {}).get("version") or "") or None
        entries = [
            VersionEntry(
                str(v["version"]),
                v.get("published"),
                prerelease(str(v["version"])),
                yanked=bool(v.get("retracted")),
            )
            for v in (data.get("versions") or [])
            if isinstance(v, dict) and v.get("version")
        ]
        entries.sort(key=lambda e: e.released or "", reverse=True)
        return VersionList(pkg_name, latest_ver, entries, len(entries), f"{PUB.page_url(pkg_name)}/versions")

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        data = await self.package(name)
        pkg_name = data.get("name") or name
        versions = data.get("versions") or []
        if version:
            target = next((v for v in versions if str(v.get("version")) == version), None)
            if not target:
                msg = f"Version `{version}` of `{pkg_name}` was not found on pub.dev."
                raise RegistryError(msg)
        else:
            target = data.get("latest") or (versions[-1] if versions else {})

        pubspec = target.get("pubspec") or {}
        groups: dict[str, list[str]] = {}
        for title, key in (("Dependencies", "dependencies"), ("Dev dependencies", "dev_dependencies")):
            raw_deps = pubspec.get(key) or {}
            if isinstance(raw_deps, dict) and raw_deps:
                formatted: list[str] = []
                for dep_name, spec in raw_deps.items():
                    if isinstance(spec, str):
                        formatted.append(f"{dep_name} {spec}".strip())
                    elif isinstance(spec, dict) and "sdk" in spec:
                        formatted.append(f"{dep_name} (sdk: {spec['sdk']})")
                    else:
                        formatted.append(dep_name)
                groups[title] = sorted(formatted, key=str.lower)

        sdk_req = (pubspec.get("environment") or {}).get("sdk")
        return DependencyList(pkg_name, str(target.get("version") or version or "latest"), groups, PUB.page_url(pkg_name), sdk_req)

    async def search(self, query: str) -> SearchResult:
        data = await self.fetch.json(
            f"{self.base}/search",
            params={"q": query},
            source="pub.dev",
            missing="pub.dev search is unavailable.",
        )
        names = [item.get("package") for item in (data.get("packages") or [])[:SEARCH_LIMIT] if isinstance(item, dict) and item.get("package")]
        if not names:
            msg = f"No Dart/Flutter packages matched {code(query)} on pub.dev."
            raise RegistryError(msg)

        details = await asyncio.gather(*(self.attempt(self.package(pkg)) for pkg in names))
        hits: list[SearchHit] = []
        for pkg_name, pkg_data in zip(names, details, strict=False):
            latest = (pkg_data or {}).get("latest") or {}
            pubspec = latest.get("pubspec") or {}
            hits.append(
                SearchHit(
                    pkg_name,
                    latest.get("version"),
                    pubspec.get("description"),
                    PUB.page_url(pkg_name),
                    latest.get("published"),
                )
            )
        return SearchResult(hits)
