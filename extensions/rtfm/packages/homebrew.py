from __future__ import annotations

from typing import Any
from urllib.parse import quote

from core.utils import code

from .constants import DOT, MAX_PACKUMENT, SEARCH_LIMIT
from .ecosystem import HOMEBREW
from .utils import DependencyList, PackageInfo, Registry, RegistryError, SearchHit, SearchResult, VersionEntry, VersionList


class HomebrewRegistry(Registry):
    ecosystem = HOMEBREW
    api_base = "https://formulae.brew.sh/api"
    _index_cache: list[dict[str, Any]] | None = None

    async def formula(self, name: str) -> dict[str, Any]:
        cleaned = name.strip().lower()
        return await self.fetch.json(
            f"{self.api_base}/formula/{quote(cleaned, safe='')}.json",
            source="Homebrew",
            missing=f"Formula `{cleaned}` was not found on Homebrew.",
        )

    async def info(self, name: str) -> PackageInfo:
        data = await self.formula(name)
        versions = data.get("versions") or {}
        stable_ver = str(versions.get("stable") or "unknown")

        analytics_30d = (((data.get("analytics") or {}).get("install") or {}).get("30d")) or {}
        downloads_30d = sum(analytics_30d.values()) if isinstance(analytics_30d, dict) else None

        runtime_deps = data.get("dependencies") or []
        reqs = [r.get("name") for r in (data.get("requirements") or []) if isinstance(r, dict) and r.get("name")]

        deprecated_msg = None
        if data.get("disabled"):
            reason = data.get("disable_reason") or "Disabled"
            deprecated_msg = f"Disabled ({reason})" + (f" since {data['disable_date']}." if data.get("disable_date") else ".")
        elif data.get("deprecated"):
            reason = data.get("deprecation_reason") or "Deprecated"
            deprecated_msg = f"Deprecated ({reason})" + (f" since {data['deprecation_date']}." if data.get("deprecation_date") else ".")

        facts_list: list[tuple[str, str]] = []
        if data.get("full_name") and data.get("full_name") != data.get("name"):
            facts_list.append(("Full name", str(data["full_name"])))
        if data.get("tap"):
            facts_list.append(("Tap", f"`{data['tap']}`"))
        if versions.get("head"):
            facts_list.append(("HEAD", f"`{versions['head']}`"))
        if data.get("keg_only"):
            facts_list.append(("Keg-only", "Yes"))

        caveats = data.get("caveats")
        warning = f"Caveats: {caveats.strip().splitlines()[0]}" if isinstance(caveats, str) and caveats.strip() else None

        fname = data.get("name") or name
        return PackageInfo(
            ecosystem=HOMEBREW,
            name=fname,
            version=stable_ver,
            url=HOMEBREW.page_url(fname),
            summary=data.get("desc"),
            license=data.get("license"),
            homepage=data.get("homepage"),
            dependencies=len(runtime_deps),
            downloads=downloads_30d,
            downloads_label="last 30 days",
            requires=", ".join([r for r in reqs if r]) if reqs else ("macOS / Linux" if versions.get("bottle") else None),
            keywords=[str(a) for a in (data.get("aliases") or [])[:8] if a],
            deprecated=deprecated_msg,
            warning=warning,
            facts=facts_list,
        )

    async def versions(self, name: str) -> VersionList:
        data = await self.formula(name)
        fname = data.get("name") or name
        versions = data.get("versions") or {}
        stable = str(versions.get("stable") or "unknown")
        revision = data.get("revision")

        entries: list[VersionEntry] = [
            VersionEntry(
                stable + (f"_{revision}" if revision else ""),
                tags=["stable", *(["bottled"] if versions.get("bottle") else [])],
                deprecated=bool(data.get("deprecated") or data.get("disabled")),
            )
        ]
        if versions.get("head"):
            entries.append(VersionEntry(str(versions["head"]), prerelease=True, tags=["HEAD"]))

        entries.extend(VersionEntry(str(v_other), note="versioned formula") for v_other in data.get("versioned_formulae") or [])

        return VersionList(fname, entries[0].version, entries, len(entries), HOMEBREW.page_url(fname))

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        data = await self.formula(name)
        fname = data.get("name") or name
        ver = str((data.get("versions") or {}).get("stable") or version or "latest")

        groups: dict[str, list[str]] = {}
        for key, label in (
            ("dependencies", "Runtime"),
            ("build_dependencies", "Build"),
            ("test_dependencies", "Test"),
            ("optional_dependencies", "Optional"),
            ("recommended_dependencies", "Recommended"),
        ):
            items = data.get(key) or []
            if items:
                groups[label] = sorted([str(i) for i in items], key=str.lower)

        reqs = [r.get("name") for r in (data.get("requirements") or []) if isinstance(r, dict) and r.get("name")]
        return DependencyList(fname, ver, groups, HOMEBREW.page_url(fname), ", ".join([r for r in reqs if r]) if reqs else None)

    async def search(self, query: str) -> SearchResult:
        q = query.strip().lower()
        if HomebrewRegistry._index_cache is None:
            HomebrewRegistry._index_cache = await self.fetch.json(
                f"{self.api_base}/formula.json",
                source="Homebrew",
                missing="Homebrew formula index is unavailable.",
                limit=MAX_PACKUMENT,
            )

        scored: list[tuple[int, dict[str, Any]]] = []
        for item in HomebrewRegistry._index_cache or []:
            fname = str(item.get("name") or "")
            desc = str(item.get("desc") or "")
            aliases = [str(a).lower() for a in (item.get("aliases") or [])]
            fname_l = fname.lower()
            desc_l = desc.lower()

            if fname_l == q or q in aliases:
                scored.append((100, item))
            elif fname_l.startswith(q):
                scored.append((80, item))
            elif q in fname_l:
                scored.append((60, item))
            elif q in desc_l:
                scored.append((30, item))

        scored.sort(key=lambda pair: (-pair[0], pair[1].get("name", "")))
        hits: list[SearchHit] = []
        for _, entry in scored[:SEARCH_LIMIT]:
            fname = entry["name"]
            ver = (entry.get("versions") or {}).get("stable")
            details = []
            if entry.get("license"):
                details.append(str(entry["license"]))
            if entry.get("deprecated"):
                details.append("deprecated")
            hits.append(
                SearchHit(
                    fname,
                    str(ver) if ver else None,
                    entry.get("desc"),
                    HOMEBREW.page_url(fname),
                    None,
                    DOT.join(details) or None,
                )
            )

        if not hits:
            msg = f"No Homebrew formulae matched {code(query)}."
            raise RegistryError(msg)
        return SearchResult(hits, len(scored))
