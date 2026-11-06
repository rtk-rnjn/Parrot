from __future__ import annotations

from typing import Any
from urllib.parse import quote

from core.utils import code

from .constants import DOT, SEARCH_LIMIT
from .ecosystem import CONDA
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
    prerelease,
    version_key,
)

DEFAULT_CHANNELS = ("conda-forge", "anaconda", "bioconda", "pytorch")


class CondaRegistry(Registry):
    ecosystem = CONDA
    api_base = "https://api.anaconda.org"

    async def resolve_package(self, name: str) -> tuple[str, str, dict[str, Any]]:
        cleaned = name.strip().strip("/")
        if "/" in cleaned:
            channel, pkg_name = cleaned.split("/", 1)
            data = await self.fetch.json(
                f"{self.api_base}/package/{quote(channel, safe='')}/{quote(pkg_name, safe='')}",
                source="Anaconda.org",
                missing=f"`{channel}/{pkg_name}` was not found on Anaconda.org.",
            )
            return channel, pkg_name, data

        for channel in DEFAULT_CHANNELS:
            data = await self.attempt(
                self.fetch.json(
                    f"{self.api_base}/package/{channel}/{quote(cleaned.lower(), safe='')}",
                    source="Anaconda.org",
                    missing="",
                )
            )
            if isinstance(data, dict) and data.get("name"):
                return channel, str(data["name"]), data

        msg = f"`{name}` was not found on Conda (checked {', '.join(DEFAULT_CHANNELS)}). Try `channel/package`."
        raise RegistryError(msg)

    async def info(self, name: str) -> PackageInfo:
        channel, pkg_name, data = await self.resolve_package(name)
        versions = [str(v) for v in (data.get("versions") or []) if v]
        latest_ver = str(data.get("latest_version") or (versions[-1] if versions else "unknown"))

        files = data.get("files") or []
        total_downloads = sum(int(f.get("ndownloads") or 0) for f in files if isinstance(f, dict))
        upload_times = [f["upload_time"] for f in files if isinstance(f, dict) and f.get("upload_time")]

        latest_files = [f for f in files if isinstance(f, dict) and str(f.get("version")) == latest_ver]
        chosen_file = latest_files[0] if latest_files else (files[-1] if files else {})
        latest_times = [f["upload_time"] for f in latest_files if f.get("upload_time")]
        deps = (chosen_file.get("dependencies") or {}).get("depends") or []

        subdirs = [str(p) for p in (data.get("conda_platforms") or []) if p]
        full_name = f"{channel}/{pkg_name}"

        facts_list: list[tuple[str, str]] = [("Channel", f"`{channel}`")]
        if subdirs:
            facts_list.append(("Platforms", ", ".join(f"`{s}`" for s in subdirs[:6])))

        return PackageInfo(
            ecosystem=CONDA,
            name=full_name,
            version=latest_ver,
            url=f"https://anaconda.org/{quote(channel, safe='')}/{quote(pkg_name, safe='')}",
            summary=data.get("summary") or data.get("description"),
            license=data.get("license"),
            author=(data.get("owner") or {}).get("login") or channel,
            homepage=data.get("home"),
            repository=normalize_repo(data.get("dev_url")),
            documentation=data.get("doc_url"),
            released=max(latest_times, default=data.get("modified_at")),
            first_release=min(upload_times, default=data.get("created_at")),
            release_count=len(versions) or None,
            dependencies=len(deps),
            downloads=total_downloads or None,
            downloads_label="all time",
            size=chosen_file.get("size"),
            requires=", ".join(subdirs[:4]) if subdirs else None,
            facts=facts_list,
        )

    async def versions(self, name: str) -> VersionList:
        channel, pkg_name, data = await self.resolve_package(name)
        files = data.get("files") or []
        ver_times: dict[str, str] = {}
        ver_counts: dict[str, int] = {}
        for f in files:
            if not isinstance(f, dict) or not f.get("version"):
                continue
            v = str(f["version"])
            ver_counts[v] = ver_counts.get(v, 0) + 1
            ut = f.get("upload_time")
            if ut and (v not in ver_times or ut > ver_times[v]):
                ver_times[v] = ut

        all_vers = [str(v) for v in (data.get("versions") or list(ver_counts.keys())) if v]
        entries = [
            VersionEntry(
                v,
                ver_times.get(v),
                prerelease(v),
                note=f"{ver_counts[v]} build{'s' if ver_counts[v] != 1 else ''}" if ver_counts.get(v) else None,
            )
            for v in all_vers
        ]
        entries.sort(key=lambda e: version_key(e.version), reverse=True)
        latest = str(data.get("latest_version") or (entries[0].version if entries else "")) or None
        full_name = f"{channel}/{pkg_name}"
        return VersionList(
            full_name,
            latest,
            entries,
            len(entries),
            f"https://anaconda.org/{quote(channel, safe='')}/{quote(pkg_name, safe='')}/files",
        )

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        channel, pkg_name, data = await self.resolve_package(name)
        target_ver = version or str(data.get("latest_version") or "")
        files = [f for f in (data.get("files") or []) if isinstance(f, dict) and str(f.get("version")) == target_ver]
        if not files and version:
            msg = f"Version `{version}` of `{channel}/{pkg_name}` was not found on Anaconda.org."
            raise RegistryError(msg)

        groups: dict[str, list[str]] = {}
        subdirs: set[str] = set()
        for f in files[:8]:
            attrs = f.get("attrs") or {}
            subdir = attrs.get("subdir") or "noarch"
            subdirs.add(subdir)
            depends = f.get("dependencies", {}).get("depends") if isinstance(f.get("dependencies"), dict) else attrs.get("depends")
            if isinstance(depends, list) and depends:
                formatted: list[str] = []
                for dep in depends:
                    if isinstance(dep, dict) and dep.get("name"):
                        specs = " ".join(str(s) for s in (dep.get("specs") or []) if s)
                        formatted.append(f"{dep['name']} {specs}".strip())
                    elif isinstance(dep, str):
                        formatted.append(dep)
                if formatted and f"Subdir: {subdir}" not in groups:
                    groups[f"Subdir: {subdir}"] = sorted(set(formatted), key=str.lower)

        full_name = f"{channel}/{pkg_name}"
        return DependencyList(
            full_name,
            target_ver or "latest",
            groups,
            f"https://anaconda.org/{quote(channel, safe='')}/{quote(pkg_name, safe='')}",
            ", ".join(sorted(subdirs)) if subdirs else None,
        )

    async def search(self, query: str) -> SearchResult:
        items = await self.fetch.json(
            f"{self.api_base}/search",
            params={"name": query},
            source="Anaconda.org",
            missing="Anaconda.org search is unavailable.",
        )
        if not isinstance(items, list) or not items:
            msg = f"No Conda packages matched {code(query)} on Anaconda.org."
            raise RegistryError(msg)

        items.sort(
            key=lambda x: (
                1 if x.get("owner") == "conda-forge" else 0,
                int(x.get("ndownloads") or 0),
            ),
            reverse=True,
        )

        hits: list[SearchHit] = []
        seen: set[str] = set()
        for entry in items:
            owner = entry.get("owner")
            pkg = entry.get("name")
            if not owner or not pkg:
                continue
            coord = f"{owner}/{pkg}"
            if coord in seen:
                continue
            seen.add(coord)

            versions = entry.get("versions") or []
            latest = versions[-1] if versions else None
            details = []
            if entry.get("ndownloads"):
                details.append(f"{compact(int(entry['ndownloads']))} downloads")
            if entry.get("conda_platforms"):
                details.append(f"{len(entry['conda_platforms'])} platforms")
            hits.append(
                SearchHit(
                    coord,
                    str(latest) if latest else None,
                    entry.get("summary"),
                    f"https://anaconda.org/{quote(owner, safe='')}/{quote(pkg, safe='')}",
                    entry.get("modified_at"),
                    DOT.join(details) or None,
                )
            )
            if len(hits) >= SEARCH_LIMIT:
                break

        return SearchResult(hits, len(items))
