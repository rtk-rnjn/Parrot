from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import quote_plus

import discord
from aiohttp import ClientResponseError
from discord.ext import commands

from .models import CodeSnippet, CVERecord, IssueOrCommitData, SecurityNewsItem
from .utils import (
    API,
    BITBUCKET_RE,
    BLUE,
    CACHE_SIZE,
    CACHE_TTL,
    CIRCL_CVE_API_URL,
    CISA_KEV_URL,
    COMMIT_RE,
    CVE_ID_RE,
    GITHUB_GIST_RE,
    GITHUB_RE,
    GITLAB_RE,
    GRAY,
    GREEN,
    ISSUE_RE,
    MAX_EMBEDS,
    MITRE_CVE_API_URL,
    NVD_API_URL,
    PURPLE,
    RED,
    SECURITY_NEWS_FEEDS,
    SHODAN_CVEDB_URL,
    SUPPRESS_ORIGINAL,
    Target,
    _get_github_raw_headers,
    _get_nvd_headers,
    _strip_html,
    _ts,
)
from .views import CodeblockPublicView, CVEPublicLayoutView, IssuePublicLayoutView, NewsPublicLayoutView

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)


class LinkToCodeblock(commands.Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.pattern_handlers: list[tuple[re.Pattern[str], Callable[..., Any]]] = [
            (GITHUB_RE, self._fetch_github_snippet),
            (GITHUB_GIST_RE, self._fetch_github_gist_snippet),
            (GITLAB_RE, self._fetch_gitlab_snippet),
            (BITBUCKET_RE, self._fetch_bitbucket_snippet),
        ]

        self.api_request_headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        if token:
            self.api_request_headers["Authorization"] = f"Bearer {token}"

        self._cache: dict[Target, tuple[float, IssueOrCommitData]] = {}
        self._cve_cache: dict[str, tuple[float, CVERecord]] = {}
        self._replies: dict[int, list[discord.Message]] = {}

        _log.debug("Cog loaded: %s", self.__class__.__name__)

    def _track_reply(self, trigger_id: int, reply: discord.Message) -> None:
        self._replies.setdefault(trigger_id, []).append(reply)
        while len(self._replies) > 200:
            self._replies.pop(next(iter(self._replies)))

    async def _fetch_response(self, url: str, response_format: str, **kwargs: Any) -> Any:
        """Makes http requests using aiohttp."""
        async with self.bot.http_session.get(url, raise_for_status=True, **kwargs) as response:
            if response_format == "text":
                return await response.text()
            if response_format == "json":
                return await response.json()
        return None

    def _find_ref(self, path: str, refs: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> tuple[str, str]:
        """Loops through all branches and tags to find the required ref."""
        ref, file_path = path.split("/", 1)
        for possible_ref in refs:
            if path.startswith(possible_ref["name"] + "/"):
                ref = possible_ref["name"]
                file_path = path[len(ref) + 1 :]
                break
        return ref, file_path

    async def _fetch_github_snippet(
        self,
        source_url: str,
        repo: str,
        path: str,
        start_line: str | int | None,
        end_line: str | int | None,
    ) -> CodeSnippet | None:
        """Fetches a snippet from a GitHub repo."""
        headers = dict(self.bot.http_session.headers)
        headers.update(_get_github_raw_headers())

        branches = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/branches",
            "json",
            headers=headers,
        )
        tags = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/tags",
            "json",
            headers=headers,
        )
        refs = branches + tags
        ref, file_path = self._find_ref(path, refs)

        file_contents = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={ref}",
            "text",
            headers=headers,
        )
        return self._build_code_snippet(file_contents, file_path, source_url, start_line, end_line)

    async def _fetch_github_gist_snippet(
        self,
        source_url: str,
        gist_id: str,
        revision: str,
        file_path: str,
        start_line: str | int | None,
        end_line: str | int | None,
    ) -> CodeSnippet | None:
        """Fetches a snippet from a GitHub gist."""
        headers = dict(self.bot.http_session.headers)
        headers.update(_get_github_raw_headers())

        gist_json: dict[str, Any] | None = await self._fetch_response(
            f"https://api.github.com/gists/{gist_id}{f'/{revision}' if revision != '' else ''}",
            "json",
            headers=headers,
        )
        if gist_json is None:
            return None

        for gist_file in gist_json["files"]:
            if file_path == gist_file.lower().replace(".", "-"):
                file_contents = await self._fetch_response(
                    gist_json["files"][gist_file]["raw_url"],
                    "text",
                )
                return self._build_code_snippet(file_contents, gist_file, source_url, start_line, end_line)
        return None

    async def _fetch_gitlab_snippet(
        self,
        source_url: str,
        repo: str,
        path: str,
        start_line: str | int | None,
        end_line: str | int | None,
    ) -> CodeSnippet | None:
        """Fetches a snippet from a GitLab repo."""
        enc_repo = quote_plus(repo)

        branches = await self._fetch_response(
            f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/branches",
            "json",
        )
        tags = await self._fetch_response(
            f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/tags",
            "json",
        )
        refs = branches + tags
        ref, file_path = self._find_ref(path, refs)
        enc_ref = quote_plus(ref)
        enc_file_path = quote_plus(file_path)

        file_contents = await self._fetch_response(
            f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/files/{enc_file_path}/raw?ref={enc_ref}",
            "text",
        )
        return self._build_code_snippet(file_contents, file_path, source_url, start_line, end_line)

    async def _fetch_bitbucket_snippet(
        self,
        source_url: str,
        repo: str,
        ref: str,
        file_path: str,
        start_line: str | int | None,
        end_line: str | int | None,
    ) -> CodeSnippet | None:
        """Fetches a snippet from a BitBucket repo."""
        file_contents = await self._fetch_response(
            f"https://bitbucket.org/{quote_plus(repo)}/raw/{quote_plus(ref)}/{quote_plus(file_path)}",
            "text",
        )
        return self._build_code_snippet(file_contents, file_path, source_url, start_line, end_line)

    def _build_code_snippet(
        self,
        file_contents: str | None,
        file_path: str,
        source_url: str,
        start_line: str | int | None,
        end_line: str | int | None,
    ) -> CodeSnippet | None:
        if not file_contents:
            return None

        if end_line is None:
            start = end = int(start_line or 0)
        else:
            start = int(start_line or 0)
            end = int(end_line)

        split_file_contents = file_contents.splitlines()
        if not split_file_contents:
            return None

        if start > end:
            start, end = end, start
        if start > len(split_file_contents) or end < 1:
            return None

        start = max(1, start)
        end = min(len(split_file_contents), end)

        language = file_path.rsplit("/", maxsplit=1)[-1].rsplit(".", maxsplit=1)[-1]
        trimmed_language = language.replace("-", "").replace("+", "").replace("_", "")
        if not trimmed_language.isalnum():
            language = ""

        return CodeSnippet(
            file_path=file_path,
            language=language,
            source_url=source_url,
            all_lines=split_file_contents,
            start_line=start,
            end_line=end,
        )

    async def _parse_snippets(self, content: str) -> list[CodeSnippet]:
        """Parse message content and return a sorted list of CodeSnippet objects."""
        all_snippets: list[tuple[int, CodeSnippet]] = []

        for pattern, handler in self.pattern_handlers:
            for match in pattern.finditer(content):
                try:
                    snippet = await handler(source_url=match.group(0), **match.groupdict())
                    if snippet is not None:
                        all_snippets.append((match.start(), snippet))
                except ClientResponseError:
                    pass

        all_snippets.sort(key=lambda pair: pair[0])
        return [pair[1] for pair in all_snippets]

    @commands.Cog.listener("on_message")
    async def on_message_codeblock(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        perms = message.channel.permissions_for(message.guild.me)
        if not perms.send_messages:
            return

        snippets = await self._parse_snippets(message.content)
        if not snippets:
            return

        view = CodeblockPublicView(snippets, author_id=message.author.id)
        content_to_send = view.build_initial_message()

        try:
            reply = await message.reply(
                content_to_send,
                view=view,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException:
            return

        self._track_reply(message.id, reply)
        if SUPPRESS_ORIGINAL and perms.manage_messages:
            with contextlib.suppress(discord.HTTPException):
                await message.edit(suppress=True)

    async def _get(self, path: str) -> dict[str, Any]:
        async with self.bot.http_session.get(
            f"{API}{path}",
            headers=self.api_request_headers,
            raise_for_status=True,
        ) as resp:
            return await resp.json()

    async def _fetch_issue_data(self, repo: str, kind: str, number: int) -> IssueOrCommitData:
        if kind == "pull":
            data = await self._get(f"/repos/{repo}/pulls/{number}")
        else:
            data = await self._get(f"/repos/{repo}/issues/{number}")
            if "pull_request" in data:  # an /issues/N link that is really a PR
                data = await self._get(f"/repos/{repo}/pulls/{number}")
                kind = "pull"
        is_pr = kind == "pull"

        if data.get("merged"):
            state_label, state_emoji, colour = "Merged", "[MERGED]", PURPLE
        elif data.get("draft"):
            state_label, state_emoji, colour = "Draft", "[DRAFT]", GRAY
        elif data["state"] == "closed":
            state_label, state_emoji, colour = "Closed", "[CLOSED]", RED
        else:
            state_label, state_emoji, colour = "Open", "[OPEN]", GREEN

        user = data.get("user") or {}
        labels = [lbl["name"] for lbl in data.get("labels", [])[:8]]

        return IssueOrCommitData(
            kind=kind,
            repo=repo,
            ident=str(number),
            title=data["title"],
            url=data["html_url"],
            body=data.get("body") or "",
            state_label=state_label,
            state_emoji=state_emoji,
            colour=colour,
            created_at=_ts(data["created_at"]),
            author_name=user.get("login", "unknown"),
            author_url=user.get("html_url"),
            author_avatar=user.get("avatar_url"),
            comments=data.get("comments", 0),
            additions=data.get("additions") if is_pr else None,
            deletions=data.get("deletions") if is_pr else None,
            changed_files=data.get("changed_files") if is_pr else None,
            labels=labels,
        )

    async def _fetch_commit_data(self, repo: str, sha: str) -> IssueOrCommitData:
        data = await self._get(f"/repos/{repo}/commits/{sha}")
        title, _, body = data["commit"]["message"].partition("\n")
        stats = data.get("stats") or {}
        gh_user = data.get("author") or {}

        return IssueOrCommitData(
            kind="commit",
            repo=repo,
            ident=data["sha"],
            title=title,
            url=data["html_url"],
            body=body,
            state_label="Commit",
            state_emoji="[COMMIT]",
            colour=BLUE,
            created_at=_ts(data["commit"]["author"]["date"]),
            author_name=gh_user.get("login") or data["commit"]["author"]["name"],
            author_url=gh_user.get("html_url"),
            author_avatar=gh_user.get("avatar_url"),
            additions=stats.get("additions", 0),
            deletions=stats.get("deletions", 0),
            changed_files=len(data.get("files", [])),
        )

    async def _data_for(self, target: Target) -> IssueOrCommitData | None:
        now = time.monotonic()
        hit = self._cache.get(target)
        if hit and now - hit[0] < CACHE_TTL:
            return hit[1]

        kind, repo, ident = target
        try:
            if kind == "commit":
                item = await self._fetch_commit_data(repo, ident)
            else:
                item = await self._fetch_issue_data(repo, kind, int(ident))
        except ClientResponseError as exc:
            if exc.status in (403, 429):
                _log.warning("GitHub rate limit hit while fetching %s", target)
            return None

        self._cache[target] = (now, item)
        while len(self._cache) > CACHE_SIZE:
            self._cache.pop(next(iter(self._cache)))
        return item

    @staticmethod
    def _find_targets(content: str) -> list[Target]:
        found: dict[Target, int] = {}
        for m in ISSUE_RE.finditer(content):
            found.setdefault((m["kind"].lower(), m["repo"].lower(), m["number"]), m.start())
        for m in COMMIT_RE.finditer(content):
            found.setdefault(("commit", m["repo"].lower(), m["sha"].lower()), m.start())
        return sorted(found, key=found.__getitem__)

    @commands.Cog.listener("on_message")
    async def on_message_issue(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        targets = self._find_targets(message.content)
        if not targets:
            return

        perms = message.channel.permissions_for(message.guild.me)
        if not (perms.send_messages and perms.embed_links):
            return

        # Fetch up to 10 targets so the user can page through all of them ephemerally,
        # while rendering the first MAX_EMBEDS (3) cards directly in the public LayoutView.
        results = await asyncio.gather(*(self._data_for(t) for t in targets[:10]))
        items = [item for item in results if item is not None]
        if not items:
            return

        layout_view = IssuePublicLayoutView(items, author_id=message.author.id)

        try:
            reply = await message.reply(
                view=layout_view,
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException:
            return

        self._track_reply(message.id, reply)
        if SUPPRESS_ORIGINAL and perms.manage_messages:
            with contextlib.suppress(discord.HTTPException):
                await message.edit(suppress=True)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        """If the user deletes their message, delete our codeblock/issue replies too."""
        replies = self._replies.pop(message.id, None)
        if replies:
            for reply in replies:
                with contextlib.suppress(discord.HTTPException):
                    await reply.delete()

    def _parse_shodan_cve(self, data: dict[str, Any]) -> CVERecord:
        cve_id = (data.get("cve_id") or data.get("id") or "UNKNOWN").upper()
        pub_dt: datetime | None = None
        if data.get("published_time"):
            with contextlib.suppress(ValueError):
                pub_dt = _ts(str(data["published_time"]))

        ghsa = data.get("ghsa") or {}
        cwe_ids = list(ghsa.get("cwe_ids") or [])

        return CVERecord(
            cve_id=cve_id,
            summary=data.get("summary") or ghsa.get("summary") or "No summary provided.",
            published=pub_dt,
            cvss=float(data["cvss"]) if data.get("cvss") is not None else None,
            cvss_version=str(data["cvss_version"]) if data.get("cvss_version") is not None else None,
            epss=float(data["epss"]) if data.get("epss") is not None else None,
            ranking_epss=float(data["ranking_epss"]) if data.get("ranking_epss") is not None else None,
            is_kev=bool(data.get("kev")),
            ransomware_campaign=data.get("ransomware_campaign"),
            proposed_action=data.get("propose_action"),
            cwe_ids=cwe_ids,
            cpes=list(data.get("cpes") or []),
            references=list(data.get("references") or []),
            sources_used=["Shodan CVEDB"],
        )

    def _parse_nvd_cve(self, vuln_obj: dict[str, Any]) -> CVERecord:
        cve = vuln_obj.get("cve") or vuln_obj
        cve_id = (cve.get("id") or "UNKNOWN").upper()

        descriptions = cve.get("descriptions") or []
        summary = next(
            (d["value"] for d in descriptions if d.get("lang") == "en" and d.get("value")),
            descriptions[0]["value"] if descriptions else "No description available.",
        )

        pub_dt: datetime | None = None
        if cve.get("published"):
            with contextlib.suppress(ValueError):
                pub_dt = _ts(str(cve["published"]))

        metrics = cve.get("metrics") or {}
        cvss_score: float | None = None
        cvss_ver: str | None = None
        for key, ver_label in (
            ("cvssMetricV40", "4.0"),
            ("cvssMetricV31", "3.1"),
            ("cvssMetricV30", "3.0"),
            ("cvssMetricV2", "2.0"),
        ):
            metric_list = metrics.get(key)
            if metric_list and isinstance(metric_list, list):
                cvss_data = metric_list[0].get("cvssData") or {}
                if cvss_data.get("baseScore") is not None:
                    cvss_score = float(cvss_data["baseScore"])
                    cvss_ver = ver_label
                    break

        cwe_ids: list[str] = []
        for w in cve.get("weaknesses") or []:
            for desc in w.get("description") or []:
                val = desc.get("value")
                if val and val not in cwe_ids and not val.startswith("NVD-CWE"):
                    cwe_ids.append(val)

        cpes: list[str] = []
        for conf in cve.get("configurations") or []:
            for node in conf.get("nodes") or []:
                for match in node.get("cpeMatch") or []:
                    crit = match.get("criteria")
                    if crit and crit not in cpes:
                        cpes.append(crit)

        refs = [r["url"] for r in (cve.get("references") or []) if r.get("url")]
        is_kev = bool(cve.get("cisaExploitAdd"))
        action = cve.get("cisaRequiredAction")

        return CVERecord(
            cve_id=cve_id,
            summary=summary,
            published=pub_dt,
            cvss=cvss_score,
            cvss_version=cvss_ver,
            is_kev=is_kev,
            proposed_action=action,
            cwe_ids=cwe_ids,
            cpes=cpes,
            references=refs,
            assigner=cve.get("sourceIdentifier"),
            state=cve.get("vulnStatus") or "PUBLISHED",
            sources_used=["NIST NVD"],
        )

    def _enrich_from_mitre_v5(self, record: CVERecord | None, data: dict[str, Any]) -> CVERecord:  # noqa: PLR0912, PLR0915
        meta = data.get("cveMetadata") or {}
        cve_id = (meta.get("cveId") or (record.cve_id if record else "UNKNOWN")).upper()
        state = meta.get("state") or "PUBLISHED"
        assigner = meta.get("assignerShortName") or meta.get("assignerOrgId")

        pub_dt: datetime | None = record.published if record else None
        if not pub_dt and meta.get("datePublished"):
            with contextlib.suppress(ValueError):
                pub_dt = _ts(str(meta["datePublished"]))

        cna = (data.get("containers") or {}).get("cna") or {}
        descriptions = cna.get("descriptions") or []
        mitre_desc = next(
            (d["value"] for d in descriptions if d.get("lang", "").startswith("en") and d.get("value")),
            descriptions[0]["value"] if descriptions else "",
        )

        cwe_ids = list(record.cwe_ids) if record else []
        for pt in cna.get("problemTypes") or []:
            for desc in pt.get("descriptions") or []:
                cwe = desc.get("cweId") or desc.get("description")
                if cwe and cwe not in cwe_ids:
                    cwe_ids.append(cwe)

        affected_products: list[str] = list(record.affected_products) if record else []
        for aff in cna.get("affected") or []:
            vendor = aff.get("vendor") or "unknown"
            product = aff.get("product") or "unknown"
            versions = [f"{v.get('version')} ({v.get('status', 'affected')})" for v in (aff.get("versions") or [])[:4] if v.get("version")]
            ver_str = f": {', '.join(versions)}" if versions else ""
            entry = f"{vendor}/{product}{ver_str}"
            if entry not in affected_products:
                affected_products.append(entry)

        credits_list: list[str] = list(record.credits) if record else []
        for cred in cna.get("credits") or []:
            val = cred.get("value")
            ctype = cred.get("type")
            if val:
                formatted = f"{val} ({ctype})" if ctype else val
                if formatted not in credits_list:
                    credits_list.append(formatted)

        cvss_score = record.cvss if record else None
        cvss_ver = record.cvss_version if record else None
        if cvss_score is None:
            for m in cna.get("metrics") or []:
                for key, ver_label in (
                    ("cvssV4_0", "4.0"),
                    ("cvssV3_1", "3.1"),
                    ("cvssV3_0", "3.0"),
                    ("cvssV2_0", "2.0"),
                ):
                    if key in m and m[key].get("baseScore") is not None:
                        cvss_score = float(m[key]["baseScore"])
                        cvss_ver = ver_label
                        break

        refs = list(record.references) if record else []
        for r in cna.get("references") or []:
            url = r.get("url")
            if url and url not in refs:
                refs.append(url)

        if record is None:
            return CVERecord(
                cve_id=cve_id,
                summary=mitre_desc or "No description provided in MITRE CVE v5 record.",
                published=pub_dt,
                cvss=cvss_score,
                cvss_version=cvss_ver,
                cwe_ids=cwe_ids,
                references=refs,
                assigner=assigner,
                state=state,
                credits=credits_list,
                affected_products=affected_products,
                sources_used=["MITRE CVE v5"],
            )

        if (not record.summary or record.summary == "No summary provided.") and mitre_desc:
            record.summary = mitre_desc
        if record.published is None:
            record.published = pub_dt
        if record.cvss is None:
            record.cvss = cvss_score
            record.cvss_version = cvss_ver
        record.assigner = record.assigner or assigner
        record.state = state or record.state
        record.cwe_ids = cwe_ids
        record.affected_products = affected_products
        record.credits = credits_list
        record.references = refs
        if "MITRE CVE v5" not in record.sources_used:
            record.sources_used.append("MITRE CVE v5")
        return record

    def _parse_circl_cve(self, data: dict[str, Any]) -> CVERecord | None:
        # CIRCL returns either legacy cve-search JSON or CVE v5 / Vulnerability-Lookup JSON
        if "cveMetadata" in data:
            rec = self._enrich_from_mitre_v5(None, data)
            rec.sources_used = ["CIRCL"]
            return rec

        cve_id = (data.get("id") or data.get("cve_id") or "").upper()
        if not cve_id:
            return None

        pub_dt: datetime | None = None
        if data.get("Published") or data.get("published"):
            with contextlib.suppress(ValueError):
                pub_dt = _ts(str(data.get("Published") or data.get("published")))

        cvss_raw = data.get("cvss") or data.get("cvss3")
        cvss_val: float | None = None
        if cvss_raw is not None:
            with contextlib.suppress(ValueError, TypeError):
                cvss_val = float(cvss_raw)

        cwe = data.get("cwe")
        cwe_ids = [cwe] if cwe and cwe != "Unknown" else []

        return CVERecord(
            cve_id=cve_id,
            summary=data.get("summary") or "No summary available.",
            published=pub_dt,
            cvss=cvss_val,
            cwe_ids=cwe_ids,
            cpes=list(data.get("vulnerable_product") or []),
            references=list(data.get("references") or []),
            assigner=data.get("assigner"),
            sources_used=["CIRCL"],
        )

    async def _fetch_enriched_cve(self, cve_id: str) -> CVERecord | None:
        """Fetch a single CVE ID combining Shodan CVEDB + MITRE CVE v5 + NVD/CIRCL fallback."""
        cve_id = cve_id.strip().upper()
        now = time.monotonic()
        cached = self._cve_cache.get(cve_id)
        if cached and now - cached[0] < CACHE_TTL:
            return cached[1]

        record: CVERecord | None = None

        # 1. Fast primary lookup via Shodan CVEDB + authoritative MITRE CVE Services API in parallel
        shodan_task = self._fetch_response(f"{SHODAN_CVEDB_URL}/cve/{cve_id}", "json")
        mitre_task = self._fetch_response(f"{MITRE_CVE_API_URL}/{cve_id}", "json")
        shodan_res, mitre_res = await asyncio.gather(shodan_task, mitre_task, return_exceptions=True)

        if isinstance(shodan_res, dict) and (shodan_res.get("cve_id") or shodan_res.get("summary")):
            record = self._parse_shodan_cve(shodan_res)

        if isinstance(mitre_res, dict) and "cveMetadata" in mitre_res:
            record = self._enrich_from_mitre_v5(record, mitre_res)

        # 2. Fallback to NIST NVD v2.0 or CIRCL if still missing
        if record is None:
            with contextlib.suppress(Exception):
                nvd_data = await self._fetch_response(
                    f"{NVD_API_URL}?cveId={cve_id}",
                    "json",
                    headers=_get_nvd_headers(),
                )
                vulns = (nvd_data or {}).get("vulnerabilities") or []
                if vulns:
                    record = self._parse_nvd_cve(vulns[0])

        if record is None:
            with contextlib.suppress(Exception):
                circl_data = await self._fetch_response(f"{CIRCL_CVE_API_URL}/cve/{cve_id}", "json")
                if isinstance(circl_data, dict):
                    record = self._parse_circl_cve(circl_data)

        if record is not None:
            self._cve_cache[cve_id] = (now, record)
            while len(self._cve_cache) > CACHE_SIZE:
                self._cve_cache.pop(next(iter(self._cve_cache)))

        return record

    async def _fetch_rss_news(self, source_key: str, *, limit: int = 12) -> list[SecurityNewsItem]:
        """Fetch and parse an RSS feed into SecurityNewsItem objects."""
        if source_key not in SECURITY_NEWS_FEEDS:
            return []
        source_name, feed_url = SECURITY_NEWS_FEEDS[source_key]
        try:
            xml_text = await self._fetch_response(feed_url, "text")
            if not xml_text:
                return []
            root = ET.fromstring(xml_text)  # noqa: S314
        except Exception as exc:
            _log.debug("Failed to fetch RSS feed %s: %s", source_key, exc)
            return []

        items: list[SecurityNewsItem] = []
        for elem in root.findall(".//item")[:limit]:
            title = (elem.findtext("title") or "Untitled Security Advisory").strip()
            link = (elem.findtext("link") or "").strip()
            desc = _strip_html(elem.findtext("description") or "")
            pub_raw = elem.findtext("pubDate")
            pub_dt: datetime | None = None
            if pub_raw:
                with contextlib.suppress(Exception):
                    pub_dt = parsedate_to_datetime(pub_raw)

            combined_text = f"{title} {desc}"
            mentioned_cves = list(dict.fromkeys(m.upper() for m in CVE_ID_RE.findall(combined_text)))

            if link:
                items.append(
                    SecurityNewsItem(
                        title=title,
                        url=link,
                        summary=desc,
                        source_name=source_name,
                        published=pub_dt,
                        cve_ids=mentioned_cves,
                    )
                )
        return items

    async def _fetch_cisa_kev_alerts(self, *, limit: int = 12) -> list[SecurityNewsItem]:
        """Fetch the most recently added actively exploited vulnerabilities from CISA's KEV catalog."""
        try:
            data = await self._fetch_response(CISA_KEV_URL, "json")
        except Exception as exc:
            _log.debug("Failed to fetch CISA KEV catalog: %s", exc)
            return []

        vulns = list((data or {}).get("vulnerabilities") or [])
        vulns.sort(key=lambda v: v.get("dateAdded", ""), reverse=True)

        alerts: list[SecurityNewsItem] = []
        for v in vulns[:limit]:
            cve_id = (v.get("cveID") or "").upper()
            vendor = v.get("vendorProject") or "Unknown Vendor"
            product = v.get("product") or "Unknown Product"
            vuln_name = v.get("vulnerabilityName") or (f"{vendor} {product} Vulnerability")
            short_desc = v.get("shortDescription") or ""
            action = v.get("requiredAction") or ""
            due_date = v.get("dueDate")
            ransomware = v.get("knownRansomwareCampaignUse")

            pub_dt: datetime | None = None
            if v.get("dateAdded"):
                with contextlib.suppress(ValueError):
                    pub_dt = datetime.fromisoformat(v["dateAdded"]).replace(tzinfo=UTC)

            summary = f"{short_desc}\n\n**Required Action:** {action}" if action else short_desc
            alerts.append(
                SecurityNewsItem(
                    title=f"[CISA KEV] {cve_id}: {vuln_name}",
                    url=(f"https://nvd.nist.gov/vuln/detail/{cve_id}" if cve_id else "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"),
                    summary=summary,
                    source_name="CISA Known Exploited Vulnerabilities",
                    published=pub_dt,
                    cve_ids=[cve_id] if cve_id else [],
                    is_kev_alert=True,
                    vendor_product=f"{vendor} - {product}",
                    due_date=due_date,
                    ransomware_use=ransomware,
                )
            )
        return alerts

    @commands.group(name="cve", invoke_without_command=True)
    async def cve_group(
        self,
        ctx: commands.Context[Bot],
        cve_id: str = commands.parameter(description=("The CVE ID to inspect (e.g., CVE-2024-3094 or CVE-2024-0204)")),
    ) -> None:
        """Look up enriched details for a specific CVE ID across Shodan CVEDB, MITRE v5, NVD, and CIRCL."""
        await ctx.defer()

        normalized = cve_id.strip().upper()
        if not CVE_ID_RE.fullmatch(normalized):
            await ctx.send(
                f"Invalid CVE format `{cve_id}`. Expected `CVE-YYYY-NNNNN` (e.g., `CVE-2024-0204`).",
                ephemeral=True,
            )
            return

        record = await self._fetch_enriched_cve(normalized)
        if record is None:
            await ctx.send(
                f"Could not find `{normalized}` across Shodan CVEDB, MITRE CVE Services, NIST NVD, or CIRCL.",
                ephemeral=True,
            )
            return

        view = CVEPublicLayoutView([record], author_id=ctx.author.id)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    @cve_group.command(name="search")
    async def cve_search(  # noqa: PLR0912
        self,
        ctx: commands.Context[Bot],
        query: str = commands.parameter(description=("Product name (e.g. nginx, openssh), vendor/product (microsoft/office), or keyword")),
        source: Literal["shodan", "nvd", "circl"] = commands.parameter(
            description=("Vulnerability database API to query (default: Shodan CVEDB)"),
            default="shodan",
        ),
        only_kev: bool = commands.parameter(
            description=("Filter to CISA Known Exploited Vulnerabilities (KEV) only"),
            default=False,
        ),
        sort_by_epss: bool = commands.parameter(
            description=("Sort results by highest EPSS exploitation probability (Shodan CVEDB only)"),
            default=False,
        ),
        severity: Literal["ALL", "LOW", "MEDIUM", "HIGH", "CRITICAL"] = (
            commands.parameter(
                description="Filter by CVSS v3 severity (NIST NVD only)",
                default="ALL",
            )
        ),
    ) -> None:
        """Search CVEs by product or keyword with ephemeral pagination across all matches."""
        await ctx.defer()
        cleaned_query = query.strip()
        records: list[CVERecord] = []

        try:
            if source == "shodan":
                params = (
                    f"product={quote_plus(cleaned_query.lower())}"
                    f"&is_kev={'true' if only_kev else 'false'}"
                    f"&sort_by_epss={'true' if sort_by_epss else 'false'}"
                    "&limit=25"
                )
                data = await self._fetch_response(f"{SHODAN_CVEDB_URL}/cves?{params}", "json")
                cves_list = (data or {}).get("cves") if isinstance(data, dict) else data
                records.extend(self._parse_shodan_cve(item) for item in (cves_list or [])[:25] if isinstance(item, dict))

            elif source == "nvd":
                params = f"keywordSearch={quote_plus(cleaned_query)}&resultsPerPage=20"
                if only_kev:
                    params += "&hasKev"
                if severity != "ALL":
                    params += f"&cvssV3Severity={severity}"
                data = await self._fetch_response(
                    f"{NVD_API_URL}?{params}",
                    "json",
                    headers=_get_nvd_headers(),
                )
                records.extend(self._parse_nvd_cve(vuln) for vuln in ((data or {}).get("vulnerabilities") or [])[:25])

            elif source == "circl":
                if "/" in cleaned_query:
                    vendor, product = cleaned_query.lower().split("/", 1)
                else:
                    vendor = product = cleaned_query.lower()
                data = await self._fetch_response(
                    f"{CIRCL_CVE_API_URL}/search/{quote_plus(vendor)}/{quote_plus(product)}",
                    "json",
                )
                raw_list: list[Any] = []
                if isinstance(data, dict):
                    raw_list = list(data.get("results") or data.get("data") or [])
                elif isinstance(data, list):
                    raw_list = data
                for item in raw_list[:25]:
                    if isinstance(item, dict):
                        parsed = self._parse_circl_cve(item)
                        if parsed:
                            records.append(parsed)
        except ClientResponseError as exc:
            await ctx.send(
                f"Upstream `{source.upper()}` API returned HTTP `{exc.status}` while searching for `{cleaned_query}`.",
                ephemeral=True,
            )
            return

        if not records:
            await ctx.send(
                f"No CVEs matched `{cleaned_query}` on **{source.upper()}** (try switching `source` between `shodan`, `nvd`, and `circl`).",
                ephemeral=True,
            )
            return

        heading = (
            f"-# **CVE Search:** `{cleaned_query}` via **{source.upper()}** | Showing top {min(len(records), MAX_EMBEDS)} of `{len(records)}` results"
        )
        view = CVEPublicLayoutView(records, author_id=ctx.author.id, heading=heading)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    @cve_group.command(name="latest")
    async def cve_latest(
        self,
        ctx: commands.Context[Bot],
        feed: Literal["circl_last", "shodan_kev", "nvd_recent"] = (
            commands.parameter(
                description=("Select the CVE feed to browse (CIRCL, Shodan CVEDB, or NIST NVD)"),
                default="shodan_kev",
            )
        ),
    ) -> None:
        """Browse the newest CVEs or highest-risk KEV vulnerabilities with ephemeral paging."""
        await ctx.defer()
        records: list[CVERecord] = []
        feed_title = ""

        try:
            if feed == "shodan_kev":
                feed_title = "Shodan CVEDB - Actively Exploited (KEV) Sorted by EPSS"
                data = await self._fetch_response(
                    f"{SHODAN_CVEDB_URL}/cves?is_kev=true&sort_by_epss=true&limit=25",
                    "json",
                )
                cves_list = (data or {}).get("cves") if isinstance(data, dict) else data
                records.extend(self._parse_shodan_cve(item) for item in (cves_list or [])[:25] if isinstance(item, dict))

            elif feed == "circl_last":
                feed_title = "CIRCL CVE-Search - Last 30 Updated CVEs"
                data = await self._fetch_response(f"{CIRCL_CVE_API_URL}/last", "json")
                if isinstance(data, list):
                    for item in data[:25]:
                        if isinstance(item, dict):
                            parsed = self._parse_circl_cve(item)
                            if parsed:
                                records.append(parsed)

            elif feed == "nvd_recent":
                feed_title = "NIST NVD - Newly Published CVEs (Last 7 Days)"
                now_utc = datetime.now(UTC)
                start_utc = now_utc - timedelta(days=7)
                pub_start = start_utc.strftime("%Y-%m-%dT%H:%M:%S.000")
                pub_end = now_utc.strftime("%Y-%m-%dT%H:%M:%S.000")
                data = await self._fetch_response(
                    f"{NVD_API_URL}?pubStartDate={pub_start}&pubEndDate={pub_end}&resultsPerPage=25",
                    "json",
                    headers=_get_nvd_headers(),
                )
                vulns = list((data or {}).get("vulnerabilities") or [])
                vulns.reverse()
                records.extend(self._parse_nvd_cve(vuln) for vuln in vulns[:25])
        except ClientResponseError as exc:
            await ctx.send(
                f"Failed to fetch `{feed}` feed (HTTP `{exc.status}`).",
                ephemeral=True,
            )
            return

        if not records:
            await ctx.send(f"No recent CVE records returned from `{feed}`.", ephemeral=True)
            return

        heading = f"-# **{feed_title}** | Loaded `{len(records)}` CVEs (use **Inspect & Page All** to browse)"
        view = CVEPublicLayoutView(records, author_id=ctx.author.id, heading=heading)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    @cve_group.command(name="news")
    async def cve_news(
        self,
        ctx: commands.Context[Bot],
        source: Literal["all", "cisa_kev", "thehackernews", "bleepingcomputer"] = commands.parameter(
            description=("Select news/advisory feed (All, CISA KEV Catalog, The Hacker News, or BleepingComputer)"),
            default="all",
        ),
        keyword: str | None = commands.parameter(
            description=("Optional keyword or CVE filter (e.g. ransomware, zero-day, linux, Fortinet)"),
            default=None,
        ),
    ) -> None:
        """Display the latest cybersecurity news and CISA KEV zero-day alerts in a LayoutView."""
        await ctx.defer()

        tasks: list[Any] = []
        if source in ("all", "cisa_kev"):
            tasks.append(self._fetch_cisa_kev_alerts(limit=10))
        if source in ("all", "thehackernews"):
            tasks.append(self._fetch_rss_news("thehackernews", limit=10))
        if source in ("all", "bleepingcomputer"):
            tasks.append(self._fetch_rss_news("bleepingcomputer", limit=10))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        items: list[SecurityNewsItem] = []
        for batch in results:
            if isinstance(batch, list):
                items.extend(batch)

        if keyword:
            kw_lower = keyword.strip().lower()
            items = [
                it
                for it in items
                if kw_lower in it.title.lower()
                or kw_lower in it.summary.lower()
                or (it.vendor_product and kw_lower in it.vendor_product.lower())
                or any(kw_lower in c.lower() for c in it.cve_ids)
            ]

        items.sort(
            key=lambda it: it.published.timestamp() if it.published else 0.0,
            reverse=True,
        )

        if not items:
            filter_note = f" matching `{keyword}`" if keyword else ""
            await ctx.send(f"No security news or KEV alerts found{filter_note}.", ephemeral=True)
            return

        filter_tag = f" | Filter: `{keyword}`" if keyword else ""
        heading = f"-# **Cybersecurity & Zero-Day Vulnerability News** ({source.upper()}){filter_tag} | `{len(items)}` items available"
        view = NewsPublicLayoutView(items[:25], author_id=ctx.author.id, heading=heading)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())
