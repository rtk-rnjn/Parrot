from __future__ import annotations

import asyncio
import datetime
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote

from core.utils import code

from .constants import DOT, SEARCH_LIMIT
from .ecosystem import MAVEN
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


def _ms_to_iso(timestamp_ms: int | None) -> str | None:
    if not timestamp_ms:
        return None
    return datetime.datetime.fromtimestamp(timestamp_ms / 1000, tz=datetime.UTC).isoformat()


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


class MavenRegistry(Registry):
    ecosystem = MAVEN
    search_url = "https://search.maven.org/solrsearch/select"
    repo_base = "https://repo1.maven.org/maven2"

    async def resolve_coordinates(self, name: str) -> tuple[str, str]:
        cleaned = name.strip()
        if ":" in cleaned:
            group_id, artifact_id = cleaned.split(":", 1)
            return group_id.strip(), artifact_id.strip()

        data = await self.fetch.json(
            self.search_url,
            params={"q": f'a:"{cleaned}"', "rows": 1, "wt": "json"},
            source="Maven Central",
            missing=f"`{cleaned}` was not found on Maven Central.",
        )
        docs = ((data.get("response") or {}).get("docs")) or []
        if not docs:
            data = await self.fetch.json(
                self.search_url,
                params={"q": cleaned, "rows": 1, "wt": "json"},
                source="Maven Central",
                missing=f"`{cleaned}` was not found on Maven Central.",
            )
            docs = ((data.get("response") or {}).get("docs")) or []

        if not docs or not docs[0].get("g") or not docs[0].get("a"):
            msg = f"`{name}` was not found on Maven Central. Use `groupId:artifactId` (e.g. `com.google.guava:guava`)."
            raise RegistryError(msg)
        return str(docs[0]["g"]), str(docs[0]["a"])

    async def fetch_versions_docs(self, group_id: str, artifact_id: str) -> list[dict[str, Any]]:
        data = await self.fetch.json(
            self.search_url,
            params={
                "q": f'g:"{group_id}" AND a:"{artifact_id}"',
                "core": "gav",
                "rows": 120,
                "wt": "json",
            },
            source="Maven Central",
            missing=f"`{group_id}:{artifact_id}` was not found on Maven Central.",
        )
        docs = ((data.get("response") or {}).get("docs")) or []
        if not docs:
            msg = f"`{group_id}:{artifact_id}` was not found on Maven Central."
            raise RegistryError(msg)
        return docs

    async def fetch_pom(self, group_id: str, artifact_id: str, version: str) -> ET.Element | None:
        group_path = "/".join(quote(part, safe="") for part in group_id.split("."))
        art = quote(artifact_id, safe="")
        ver = quote(version, safe="")
        url = f"{self.repo_base}/{group_path}/{art}/{ver}/{artifact_id}-{version}.pom"
        xml_text = await self.attempt(self.fetch.text(url, source="Maven Central", missing=""))
        if not xml_text:
            return None
        try:
            return await asyncio.to_thread(ET.fromstring, xml_text)
        except ET.ParseError:
            return None

    @staticmethod
    def parse_pom_metadata(root: ET.Element | None) -> dict[str, Any]:  # noqa: PLR0912
        if root is None:
            return {}

        props: dict[str, str] = {}
        licenses: list[str] = []
        developers: list[str] = []
        deps_by_scope: dict[str, list[str]] = {}
        description: str | None = None
        url: str | None = None
        scm_url: str | None = None

        for child in root:
            tag = _strip_ns(child.tag)
            if tag == "properties":
                for prop in child:
                    if prop.text and prop.text.strip():
                        props[_strip_ns(prop.tag)] = prop.text.strip()
            elif tag == "description" and child.text:
                description = " ".join(child.text.split())
            elif tag == "url" and child.text:
                url = child.text.strip()
            elif tag == "scm":
                for sub in child:
                    if _strip_ns(sub.tag) in ("url", "connection") and sub.text and not scm_url:
                        scm_url = sub.text.strip().removeprefix("scm:git:")
            elif tag == "licenses":
                for lic in child:
                    licenses.extend(sub.text.strip() for sub in lic if _strip_ns(sub.tag) == "name" and sub.text)
            elif tag == "developers":
                for dev in child:
                    for sub in dev:
                        if _strip_ns(sub.tag) in ("name", "id") and sub.text:
                            developers.append(sub.text.strip())
                            break
            elif tag == "dependencies":
                for dep in child:
                    g_val = a_val = v_val = scope_val = None
                    optional_val = False
                    for sub in dep:
                        stag = _strip_ns(sub.tag)
                        text_val = (sub.text or "").strip()
                        if stag == "groupId":
                            g_val = text_val
                        elif stag == "artifactId":
                            a_val = text_val
                        elif stag == "version":
                            v_val = text_val
                        elif stag == "scope":
                            scope_val = text_val
                        elif stag == "optional":
                            optional_val = text_val.lower() == "true"

                    if g_val and a_val:
                        if v_val and v_val.startswith("${") and v_val.endswith("}"):
                            v_val = props.get(v_val[2:-1], v_val)
                        coord = f"{g_val}:{a_val}" + (f":{v_val}" if v_val else "")
                        group_label = "Optional" if optional_val else (scope_val or "compile").capitalize()
                        deps_by_scope.setdefault(group_label, []).append(coord)

        java_req = props.get("maven.compiler.release") or props.get("maven.compiler.target") or props.get("java.version") or props.get("jdk.version")
        return {
            "description": description,
            "homepage": url,
            "repository": normalize_repo(scm_url),
            "license": ", ".join(licenses[:3]) if licenses else None,
            "author": ", ".join(developers[:3]) if developers else None,
            "dependencies": deps_by_scope,
            "java_version": java_req,
        }

    async def info(self, name: str) -> PackageInfo:
        group_id, artifact_id = await self.resolve_coordinates(name)
        docs = await self.fetch_versions_docs(group_id, artifact_id)
        docs.sort(key=lambda d: version_key(str(d.get("v", ""))), reverse=True)
        stable_docs = [d for d in docs if not prerelease(str(d.get("v", "")))]
        latest_doc = stable_docs[0] if stable_docs else docs[0]
        latest_ver = str(latest_doc.get("v") or "unknown")

        pom_root = await self.fetch_pom(group_id, artifact_id, latest_ver)
        pom_meta = self.parse_pom_metadata(pom_root)

        timestamps = [d["timestamp"] for d in docs if d.get("timestamp")]
        deps_groups: dict[str, list[str]] = pom_meta.get("dependencies") or {}
        runtime_deps = len(deps_groups.get("Compile", [])) + len(deps_groups.get("Runtime", []))

        coord = f"{group_id}:{artifact_id}"
        page_url = f"https://central.sonatype.com/artifact/{quote(group_id, safe='')}/{quote(artifact_id, safe='')}"
        packaging = latest_doc.get("p") or "jar"

        facts_list: list[tuple[str, str]] = [("Group ID", f"`{group_id}`"), ("Artifact ID", f"`{artifact_id}`"), ("Packaging", f"`{packaging}`")]
        javadoc_url = f"https://javadoc.io/doc/{quote(group_id, safe='')}/{quote(artifact_id, safe='')}/{quote(latest_ver, safe='')}"

        return PackageInfo(
            ecosystem=MAVEN,
            name=coord,
            version=latest_ver,
            url=page_url,
            summary=pom_meta.get("description"),
            license=pom_meta.get("license"),
            author=pom_meta.get("author"),
            homepage=pom_meta.get("homepage"),
            repository=pom_meta.get("repository"),
            documentation=javadoc_url,
            released=_ms_to_iso(latest_doc.get("timestamp")),
            first_release=_ms_to_iso(min(timestamps, default=None)),
            release_count=len(docs),
            dependencies=runtime_deps,
            requires=pom_meta.get("java_version"),
            keywords=[str(t) for t in (latest_doc.get("tags") or [])[:10] if t],
            facts=facts_list,
        )

    async def versions(self, name: str) -> VersionList:
        group_id, artifact_id = await self.resolve_coordinates(name)
        docs = await self.fetch_versions_docs(group_id, artifact_id)
        entries = [
            VersionEntry(
                str(d["v"]),
                _ms_to_iso(d.get("timestamp")),
                prerelease(str(d["v"])),
            )
            for d in docs
            if d.get("v")
        ]
        entries.sort(key=lambda e: version_key(e.version), reverse=True)
        latest = next((e.version for e in entries if not e.prerelease), entries[0].version if entries else None)
        coord = f"{group_id}:{artifact_id}"
        page_url = f"https://central.sonatype.com/artifact/{quote(group_id, safe='')}/{quote(artifact_id, safe='')}/versions"
        return VersionList(coord, latest, entries, len(entries), page_url)

    async def dependencies(self, name: str, version: str | None) -> DependencyList:
        group_id, artifact_id = await self.resolve_coordinates(name)
        if not version:
            docs = await self.fetch_versions_docs(group_id, artifact_id)
            docs.sort(key=lambda d: version_key(str(d.get("v", ""))), reverse=True)
            stable = [d for d in docs if not prerelease(str(d.get("v", "")))]
            version = str((stable[0] if stable else docs[0]).get("v"))

        pom_root = await self.fetch_pom(group_id, artifact_id, version)
        if pom_root is None:
            msg = f"Could not find POM metadata for `{group_id}:{artifact_id}:{version}` on Maven Central."
            raise RegistryError(msg)

        pom_meta = self.parse_pom_metadata(pom_root)
        groups: dict[str, list[str]] = pom_meta.get("dependencies") or {}
        ordered = {k: sorted(v, key=str.lower) for k, v in groups.items()}
        coord = f"{group_id}:{artifact_id}"
        page_url = f"https://central.sonatype.com/artifact/{quote(group_id, safe='')}/{quote(artifact_id, safe='')}/{quote(version, safe='')}"
        return DependencyList(coord, version, ordered, page_url, pom_meta.get("java_version"))

    async def search(self, query: str) -> SearchResult:
        data = await self.fetch.json(
            self.search_url,
            params={"q": query, "rows": SEARCH_LIMIT, "wt": "json"},
            source="Maven Central",
            missing="Maven Central search is unavailable.",
        )
        response = data.get("response") or {}
        hits: list[SearchHit] = []
        for doc in (response.get("docs") or [])[:SEARCH_LIMIT]:
            g = doc.get("g")
            a = doc.get("a")
            if not g or not a:
                continue
            coord = f"{g}:{a}"
            ver = doc.get("latestVersion") or doc.get("v")
            details = []
            if doc.get("p"):
                details.append(f"packaging `{doc['p']}`")
            if doc.get("versionCount"):
                details.append(f"{doc['versionCount']} versions")
            hits.append(
                SearchHit(
                    coord,
                    ver,
                    None,
                    f"https://central.sonatype.com/artifact/{quote(g, safe='')}/{quote(a, safe='')}",
                    _ms_to_iso(doc.get("timestamp")),
                    DOT.join(details) or None,
                )
            )
        if not hits:
            msg = f"No artifacts matched {code(query)} on Maven Central."
            raise RegistryError(msg)
        return SearchResult(hits, response.get("numFound"))
