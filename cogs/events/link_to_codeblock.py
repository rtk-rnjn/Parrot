from __future__ import annotations

import logging
import os
import re
import textwrap
from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus

import discord
from aiohttp import ClientResponseError
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import Parrot

_log = logging.getLogger("bot.cogs.link_to_codeblock")

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


class LinkToCodeblock(commands.Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.pattern_handlers: list[tuple[re.Pattern[str], Callable]] = [
            (GITHUB_RE, self._fetch_github_snippet),
            (GITHUB_GIST_RE, self._fetch_github_gist_snippet),
            (GITLAB_RE, self._fetch_gitlab_snippet),
            (BITBUCKET_RE, self._fetch_bitbucket_snippet),
        ]

        _log.info("Cog loaded: %s", self.__class__.__name__)

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

    async def _fetch_github_snippet(self, repo: str, path: str, start_line: str | int | None, end_line: str | int | None) -> str:
        """Fetches a snippet from a GitHub repo."""
        # Search the GitHub API for the specified branch
        branches = await self._fetch_response(f"https://api.github.com/repos/{repo}/branches", "json", headers=GITHUB_HEADERS)
        tags = await self._fetch_response(f"https://api.github.com/repos/{repo}/tags", "json", headers=GITHUB_HEADERS)
        refs = branches + tags
        ref, file_path = self._find_ref(path, refs)

        file_contents = await self._fetch_response(
            f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={ref}",
            "text",
            headers=GITHUB_HEADERS,
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
        gist_json: dict | None = await self._fetch_response(
            f"https://api.github.com/gists/{gist_id}{f'/{revision}' if revision != '' else ''}",
            "json",
            headers=GITHUB_HEADERS,
        )

        if gist_json is None:
            return ""

        # Check each file in the gist for the specified file
        for gist_file in gist_json["files"]:
            if file_path == gist_file.lower().replace(".", "-"):
                file_contents = await self._fetch_response(gist_json["files"][gist_file]["raw_url"], "text")
                return self._snippet_to_codeblock(file_contents, gist_file, start_line, end_line)
        return ""

    async def _fetch_gitlab_snippet(self, repo: str, path: str, start_line: str | int | None, end_line: str | int | None) -> str:
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
        file_contents = await self._fetch_response(f"https://bitbucket.org/{quote_plus(repo)}/raw/{quote_plus(ref)}/{quote_plus(file_path)}", "text")
        return self._snippet_to_codeblock(file_contents, file_path, start_line, end_line)

    def _snippet_to_codeblock(self, file_contents: Any | None, file_path: str, start_line: str | int | None, end_line: str | int | None) -> str:
        """Given the entire file contents and target lines, creates a code block.
        First, we split the file contents into a list of lines and then keep and join only the required
        ones together.
        We then dedent the lines to look nice, and replace all ` characters with `\u200b to prevent
        markdown injection.
        Finally, we surround the code with ``` characters.
        """
        # Parse start_line and end_line into integers
        if end_line is None:
            start_line = end_line = int(start_line or 0)
        else:
            start_line = int(start_line or 0)
            end_line = int(end_line)

        split_file_contents = file_contents.splitlines() if file_contents else []

        # Make sure that the specified lines are in range
        if start_line > end_line:
            start_line, end_line = end_line, start_line
        if start_line > len(split_file_contents) or end_line < 1:
            return ""
        start_line = max(1, start_line)
        end_line = min(len(split_file_contents), end_line)

        # Gets the code lines, dedents them, and inserts zero-width spaces to prevent Markdown injection
        required = "\n".join(split_file_contents[start_line - 1 : end_line])
        required = textwrap.dedent(required).rstrip().replace("`", "`\u200b")

        # Extracts the code language and checks whether it's a "valid" language
        language = file_path.rsplit("/", maxsplit=1)[-1].rsplit(".", maxsplit=1)[-1]
        trimmed_language = language.replace("-", "").replace("+", "").replace("_", "")
        is_valid_language = trimmed_language.isalnum()
        if not is_valid_language:
            language = ""

        # Adds a label showing the file path to the snippet
        if start_line == end_line:
            ret = f"`{file_path}` line {start_line}\n"
        else:
            ret = f"`{file_path}` lines {start_line} to {end_line}\n"

        if len(required) != 0:
            return f"{ret}```{language}\n{required}```"
        # Returns an empty codeblock if the snippet is empty
        return f"{ret}``` ```"

    async def _parse_snippets(self, content: str) -> str:
        """Parse message content and return a string with a code block for each URL found."""
        all_snippets: list[tuple[int, str]] = []

        for pattern, handler in self.pattern_handlers:
            for match in pattern.finditer(content):
                try:
                    snippet = await handler(**match.groupdict())
                    all_snippets.append((match.start(), snippet))
                except ClientResponseError as error:
                    error_message = error.message
                    print(error_message)

        # Sorts the list of snippets by their match index and joins them into a single message
        return "\n".join(x[1] for x in sorted(all_snippets))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        assert isinstance(message.author, discord.Member)

        message_to_send = await self._parse_snippets(message.content)
        if 0 < len(message_to_send) < 2000 and message.guild.me.guild_permissions.send_messages:
            await message.reply(message_to_send, mention_author=False)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(LinkToCodeblock(bot))
