from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import re
import textwrap
import time
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus

import discord
from aiohttp import ClientResponseError
from discord.ext import commands

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)

DISCORD_MESSAGE_LIMIT = 2000

GITHUB_RE = re.compile(
    r"https://github\.com/(?P<repo>[a-zA-Z0-9-]+/[\w.-]+)/blob/"
    r"(?P<path>[^#>]+)(\?[^#>]+)?(#L(?P<start_line>\d+)(([-~:]|(\.\.))L(?P<end_line>\d+))?)",
    re.IGNORECASE,
)

GITHUB_GIST_RE = re.compile(
    r"https://gist\.github\.com/([a-zA-Z0-9-]+)/(?P<gist_id>[a-zA-Z0-9]+)/*"
    r"(?P<revision>[a-zA-Z0-9]*)/*#file-(?P<file_path>[^#>]+?)(\?[^#>]+)?"
    r"(-L(?P<start_line>\d+)([-~:]L(?P<end_line>\d+))?)",
    re.IGNORECASE,
)

GITLAB_RE = re.compile(
    r"https://gitlab\.com/(?P<repo>[\w.-]+/[\w.-]+)/\-/blob/(?P<path>[^#>]+)"
    r"(\?[^#>]+)?(#L(?P<start_line>\d+)(-(?P<end_line>\d+))?)",
    re.IGNORECASE,
)

BITBUCKET_RE = re.compile(
    r"https://bitbucket\.org/(?P<repo>[a-zA-Z0-9-]+/[\w.-]+)/src/(?P<ref>[0-9a-zA-Z]+)"
    r"/(?P<file_path>[^#>]+)(\?[^#>]+)?(#lines-(?P<start_line>\d+)(:(?P<end_line>\d+))?)",
    re.IGNORECASE,
)

GITHUB_HEADERS = {
    "Accept": "application/vnd.github.v3.raw",
    "Authorization": f"token {os.environ['GITHUB_PERSONAL_ACCESS_TOKEN']}",
}


API = "https://api.github.com"
MAX_EMBEDS = 3
CACHE_TTL = 120.0
CACHE_SIZE = 256
SUPPRESS_ORIGINAL = True

GREEN, RED, PURPLE, GRAY, BLUE = 0x2DA44E, 0xCF222E, 0x8250DF, 0x6E7781, 0x1F6FEB

_REPO = r"(?P<repo>[\w.-]+/[\w.-]+)"
ISSUE_RE = re.compile(
    rf"(?<!<)https://github\.com/{_REPO}/(?P<kind>issues|pull)/(?P<number>\d+)\b",
    re.IGNORECASE,
)
COMMIT_RE = re.compile(
    rf"(?<!<)https://github\.com/{_REPO}/commit/(?P<sha>[0-9a-f]{{7,40}})\b",
    re.IGNORECASE,
)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


Target = tuple[str, str, str]


def _trim(text: str | None, limit: int = 300) -> str:
    """Strip issue-template comments, collapse blank lines and shorten to ``limit``."""
    text = _HTML_COMMENT_RE.sub("", text or "")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "\N{HORIZONTAL ELLIPSIS}"
    if text.count("```") % 2:
        text += "\n```"
    return text


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class LinkToCodeblock(commands.Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.pattern_handlers: list[tuple[re.Pattern[str], Callable]] = [
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
        self._cache: dict[Target, tuple[float, discord.Embed]] = {}
        self._replies: dict[int, discord.Message] = {}

        _log.debug("Cog loaded: %s", self.__class__.__name__)

    async def _fetch_response(self, url: str, response_format: str, **kwargs: Any) -> Any:
        """Makes http requests using aiohttp."""
        async with self.bot.http_session.get(url, raise_for_status=True, **kwargs) as response:
            if response_format == "text":
                return await response.text()
            if response_format == "json":
                return await response.json()
        return None

    def _find_ref(self, path: str, refs: tuple) -> tuple:
        """Loops through all branches and tags to find the required ref."""
        # Base case: there is no slash in the branch name
        ref, file_path = path.split("/", 1)
        # In case there are slashes in the branch name, we loop through all branches and tags
        for possible_ref in refs:
            if path.startswith(possible_ref["name"] + "/"):
                ref = possible_ref["name"]
                file_path = path[len(ref) + 1 :]
                break
        return ref, file_path

    async def _fetch_github_snippet(
        self,
        repo: str,
        path: str,
        start_line: str | int | None,
        end_line: str | int | None,
    ) -> str:
        """Fetches a snippet from a GitHub repo."""
        # Search the GitHub API for the specified branch
        headers = dict(self.bot.http_session.headers)
        headers.update(GITHUB_HEADERS)

        branches = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/branches",
            "json",
            headers=headers,
        )
        tags = await self._fetch_response(f"https://api.github.com/repos/{repo}/tags", "json", headers=headers)
        refs = branches + tags
        ref, file_path = self._find_ref(path, refs)

        file_contents = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={ref}",
            "text",
            headers=headers,
        )
        return self._snippet_to_codeblock(file_contents, file_path, start_line, end_line)

    async def _fetch_github_gist_snippet(
        self,
        gist_id: str,
        revision: str,
        file_path: str,
        start_line: str | int | None,
        end_line: str | int | None,
    ) -> str:
        """Fetches a snippet from a GitHub gist."""
        headers = dict(self.bot.http_session.headers)
        headers.update(GITHUB_HEADERS)

        gist_json: dict | None = await self._fetch_response(
            f"https://api.github.com/gists/{gist_id}{f'/{revision}' if revision != '' else ''}",
            "json",
            headers=headers,
        )

        if gist_json is None:
            return ""

        # Check each file in the gist for the specified file
        for gist_file in gist_json["files"]:
            if file_path == gist_file.lower().replace(".", "-"):
                file_contents = await self._fetch_response(gist_json["files"][gist_file]["raw_url"], "text")
                return self._snippet_to_codeblock(file_contents, gist_file, start_line, end_line)
        return ""

    async def _fetch_gitlab_snippet(
        self,
        repo: str,
        path: str,
        start_line: str | int | None,
        end_line: str | int | None,
    ) -> str:
        """Fetches a snippet from a GitLab repo."""
        enc_repo = quote_plus(repo)

        # Searches the GitLab API for the specified branch
        branches = await self._fetch_response(f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/branches", "json")
        tags = await self._fetch_response(f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/tags", "json")
        refs = branches + tags
        ref, file_path = self._find_ref(path, refs)
        enc_ref = quote_plus(ref)
        enc_file_path = quote_plus(file_path)

        file_contents = await self._fetch_response(
            f"https://gitlab.com/api/v4/projects/{enc_repo}/repository/files/{enc_file_path}/raw?ref={enc_ref}",
            "text",
        )
        return self._snippet_to_codeblock(file_contents, file_path, start_line, end_line)

    async def _fetch_bitbucket_snippet(self, repo: str, ref: str, file_path: str, start_line: str, end_line: str) -> str:
        """Fetches a snippet from a BitBucket repo."""
        file_contents = await self._fetch_response(
            f"https://bitbucket.org/{quote_plus(repo)}/raw/{quote_plus(ref)}/{quote_plus(file_path)}",
            "text",
        )
        return self._snippet_to_codeblock(file_contents, file_path, start_line, end_line)

    def _snippet_to_codeblock(
        self,
        file_contents: Any | None,
        file_path: str,
        start_line: str | int | None,
        end_line: str | int | None,
    ) -> str:
        if end_line is None:
            start_line = end_line = int(start_line or 0)
        else:
            start_line = int(start_line or 0)
            end_line = int(end_line)

        split_file_contents = file_contents.splitlines() if file_contents else []

        if start_line > end_line:
            start_line, end_line = end_line, start_line
        if start_line > len(split_file_contents) or end_line < 1:
            return ""
        start_line = max(1, start_line)
        end_line = min(len(split_file_contents), end_line)

        required = "\n".join(split_file_contents[start_line - 1 : end_line])
        required = textwrap.dedent(required).rstrip().replace("`", "`\N{ZERO WIDTH SPACE}")

        language = file_path.rsplit("/", maxsplit=1)[-1].rsplit(".", maxsplit=1)[-1]
        trimmed_language = language.replace("-", "").replace("+", "").replace("_", "")
        is_valid_language = trimmed_language.isalnum()
        if not is_valid_language:
            language = ""

        ret = f"`{file_path}` line {start_line}\n" if start_line == end_line else f"`{file_path}` lines {start_line} to {end_line}\n"

        if len(required) != 0:
            return f"{ret}```{language}\n{required}```"

        return f"{ret}``` ```"

    async def _parse_snippets(self, content: str) -> str:
        """Parse message content and return a string with a code block for each URL found."""
        all_snippets: list[tuple[int, str]] = []

        for pattern, handler in self.pattern_handlers:
            for match in pattern.finditer(content):
                try:
                    snippet = await handler(**match.groupdict())
                    all_snippets.append((match.start(), snippet))
                except ClientResponseError:
                    pass

        return "\n".join(x[1] for x in sorted(all_snippets))

    @commands.Cog.listener("on_message")
    async def on_message_codeblock(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        assert isinstance(message.author, discord.Member)

        message_to_send = await self._parse_snippets(message.content)
        if 0 < len(message_to_send) < DISCORD_MESSAGE_LIMIT and message.guild.me.guild_permissions.send_messages:
            reply = await message.reply(message_to_send, mention_author=False)
            self._replies[message.id] = reply

    async def _get(self, path: str) -> dict:
        async with self.bot.http_session.get(f"{API}{path}", headers=self.api_request_headers, raise_for_status=True) as resp:
            return await resp.json()

    async def _issue_embed(self, repo: str, kind: str, number: int) -> discord.Embed:
        if kind == "pull":
            data = await self._get(f"/repos/{repo}/pulls/{number}")
        else:
            data = await self._get(f"/repos/{repo}/issues/{number}")
            if "pull_request" in data:  # an /issues/N link that is really a PR
                data = await self._get(f"/repos/{repo}/pulls/{number}")
                kind = "pull"
        is_pr = kind == "pull"

        if data.get("merged"):
            state, colour = "Merged", PURPLE
        elif data.get("draft"):
            state, colour = "Draft", GRAY
        elif data["state"] == "closed":
            state, colour = "Closed", RED
        else:
            state, colour = "Open", GREEN

        embed = discord.Embed(
            title=f"{'PR' if is_pr else 'Issue'} #{number}: {data['title']}"[:256],
            url=data["html_url"],
            description=_trim(data.get("body")),
            colour=colour,
            timestamp=_ts(data["created_at"]),
        )
        embed.add_field(name="State", value=state)
        embed.add_field(name="Comments", value=str(data.get("comments", 0)))
        if is_pr:
            embed.add_field(
                name="Changes",
                value=f"+{data['additions']} \N{MINUS SIGN}{data['deletions']} \N{BULLET} {data['changed_files']} files",
            )
        labels = ", ".join(lbl["name"] for lbl in data.get("labels", [])[:6])
        if labels:
            embed.add_field(name="Labels", value=labels, inline=False)
        user = data.get("user")
        if user:
            embed.set_author(name=user["login"], url=user["html_url"], icon_url=user["avatar_url"])
        embed.set_footer(text=repo)
        return embed

    async def _commit_embed(self, repo: str, sha: str) -> discord.Embed:
        data = await self._get(f"/repos/{repo}/commits/{sha}")
        title, _, body = data["commit"]["message"].partition("\n")
        embed = discord.Embed(
            title=title[:256],
            url=data["html_url"],
            description=_trim(body),
            colour=BLUE,
            timestamp=_ts(data["commit"]["author"]["date"]),
        )
        stats = data.get("stats", {})
        embed.add_field(
            name="Changes",
            value=f"+{stats.get('additions', 0)} \N{MINUS SIGN}{stats.get('deletions', 0)} \N{BULLET} {len(data.get('files', []))} files",
        )

        gh_user = data.get("author") or {}
        embed.set_author(
            name=gh_user.get("login") or data["commit"]["author"]["name"],
            url=gh_user.get("html_url"),
            icon_url=gh_user.get("avatar_url"),
        )
        embed.set_footer(text=f"{repo}@{data['sha'][:7]}")
        return embed

    async def _embed_for(self, target: Target) -> discord.Embed | None:
        now = time.monotonic()
        hit = self._cache.get(target)
        if hit and now - hit[0] < CACHE_TTL:
            return hit[1].copy()

        kind, repo, ident = target
        try:
            if kind == "commit":
                embed = await self._commit_embed(repo, ident)
            else:
                embed = await self._issue_embed(repo, kind, int(ident))
        except ClientResponseError as exc:
            if exc.status in (403, 429):
                _log.warning("GitHub rate limit hit while embedding %s", target)
            return None

        self._cache[target] = (now, embed)
        while len(self._cache) > CACHE_SIZE:
            self._cache.pop(next(iter(self._cache)))
        return embed.copy()

    @staticmethod
    def _find_targets(content: str) -> list[Target]:
        found: dict[Target, int] = {}
        for m in ISSUE_RE.finditer(content):
            found.setdefault((m["kind"].lower(), m["repo"].lower(), m["number"]), m.start())
        for m in COMMIT_RE.finditer(content):
            found.setdefault(("commit", m["repo"].lower(), m["sha"].lower()), m.start())
        return sorted(found, key=found.__getitem__)  # keep the order they appeared in

    @commands.Cog.listener("on_message")
    async def on_message_issue(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return
        targets = self._find_targets(message.content)[:MAX_EMBEDS]
        if not targets:
            return
        perms = message.channel.permissions_for(message.guild.me)
        if not (perms.send_messages and perms.embed_links):
            return

        results = await asyncio.gather(*(self._embed_for(t) for t in targets))
        embeds = [e for e in results if e is not None]
        if not embeds:
            return

        try:
            reply = await message.reply(embeds=embeds, mention_author=False, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            return
        self._replies[message.id] = reply
        while len(self._replies) > 200:
            self._replies.pop(next(iter(self._replies)))
        if SUPPRESS_ORIGINAL and perms.manage_messages:
            with contextlib.suppress(discord.HTTPException):
                await message.edit(suppress=True)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        """If the user deletes their message, delete our embed reply too."""
        reply = self._replies.pop(message.id, None)
        if reply:
            with contextlib.suppress(discord.HTTPException):
                await reply.delete()
