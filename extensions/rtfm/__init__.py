from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import html
import inspect
import json
import logging
import os
import re
import unicodedata
import urllib.parse
from html import unescape
from typing import TYPE_CHECKING, Annotated, Literal
from urllib.parse import quote_plus, urljoin

import aiohttp
import discord
import rapidfuzz
import re2
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from discord.ext import commands, tasks
from jishaku.codeblocks import Codeblock, codeblock_converter

from core.utils import PaginationView, truncate

from .cheat_sh import CheatSheet
from .constants import (
    MINIMUM_CERTAINTY,
    REAL_PYTHON_BASE_URL,
    REAL_PYTHON_ROOT_API,
    REAL_PYTHON_SEARCH_URL,
    STACKOVERFLOW_BASE_API,
    STACKOVERFLOW_PARAMS,
    STACKOVERFLOW_SEARCH_URL,
    WTF_PYTHON_BASE_URL,
    WTF_PYTHON_RAW_URL,
)
from .docs import Docs
from .github import GitHub
from .hacker_news import HackerNews
from .javascript import JavaScript
from .kontests import Kontests
from .packages import Packages
from .python import Python
from .syntax import Syntax
from .used import build_embeds, execute_run, parse_man_page

try:
    import lxml  # noqa: F401  # pylint: disable=unused-import

    HTML_PARSER = "lxml"
except ImportError:
    HTML_PARSER = "html.parser"

if TYPE_CHECKING:
    from core import Bot


_log = logging.getLogger(__name__)
HTTP_OK = 200
EMBED_FIELD_LIMIT = 1024
MIN_TUTORIAL_SCORE = 50
DISCORD_MESSAGE_LIMIT = 2000

DEPENDENCIES = [Packages, GitHub, Docs, Kontests, Syntax, Python, JavaScript, HackerNews]


class Developer(*DEPENDENCIES, commands.Cog):
    """To test code and check docs."""

    help_emoji = "\N{PERSONAL COMPUTER}"

    def __init__(self, bot: Bot) -> None:
        for Cog in DEPENDENCIES:
            Cog.__init__(self, bot)

        self.bot = bot
        self.algos = sorted([h for h in hashlib.algorithms_available if h.islower()])
        self.wtf_section_links: dict[str, str] = {}

        self.cheat_repository = CheatSheet(self.bot)
        self.github_access_token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")

        _log.debug("Cog loaded: %s", self.__class__.__name__)

    @tasks.loop(minutes=60)
    async def fetch_readme(self) -> None:
        """Gets the content of README.md from the WTF Python Repository."""
        async with self.bot.http_session.get(f"{WTF_PYTHON_RAW_URL}README.md") as resp:
            if resp.status == HTTP_OK:
                raw = await resp.text()
                self.parse_readme(raw)

    def parse_readme(self, data: str) -> None:
        # Match the start of examples, until the end of the table of contents (toc)
        example_section_match = re.search(r"\[\N{EYES} Examples\]\(#-examples\)\n([\w\W]*)<!-- tocstop -->", data)
        if not example_section_match:
            return
        table_of_contents = example_section_match[0].split("\n")

        for header in list(map(str.strip, table_of_contents)):
            example_section_match = re.search(r"\[\N{BLACK RIGHT-POINTING TRIANGLE} (.*)\]\((.*)\)", header)
            if example_section_match:
                hyper_link = example_section_match[0].split("(")[1].replace(")", "")
                self.wtf_section_links[example_section_match[0]] = f"{WTF_PYTHON_BASE_URL}/{hyper_link}"

    def wtf_fuzzy_match_header(self, query: str) -> str | None:
        data = rapidfuzz.process.extractOne(query, self.wtf_section_links.keys())
        if data is None:
            return None
        match, certainty, _ = data
        return match if certainty > MINIMUM_CERTAINTY else None

    def get_content(self, tag: BeautifulSoup | Tag | None):
        """Returns content between two h2 tags."""
        if tag is None:
            return ""

        bssiblings = tag.next_siblings
        siblings = []
        for elem in bssiblings:
            # get only tag elements, before the next h2
            # Putting away the comments, we know there's
            # at least one after it.
            if type(elem) is NavigableString:
                continue
            # It's a tag
            if isinstance(elem, Tag) and elem.name == "h2":
                break
            siblings.append(elem.text)
        content = "\n".join(siblings)
        if len(content) >= EMBED_FIELD_LIMIT:
            content = f"{content[:1021]}..."

        return re.sub(r" +", " ", content)

    @property
    def session(self):
        return self.bot.http_session

    @commands.command()
    async def run(
        self,
        ctx: commands.Context[Bot],
        *,
        codeblock: Annotated[Codeblock, codeblock_converter] = commands.parameter(description="Code block to run."),  # noqa: B008
    ) -> discord.Message:
        """Run code in various languages."""
        language = codeblock.language
        if language is None:
            raise commands.MissingRequiredArgument(commands.Parameter(name="language", kind=inspect.Parameter.POSITIONAL_ONLY))

        async with ctx.typing():
            output = await execute_run(language, codeblock.content)

            return await ctx.reply(output)

    @commands.command()
    async def man(
        self,
        ctx: commands.Context[Bot],
        *,
        page: str = commands.parameter(description="The manual page to get."),
    ) -> discord.Message | None:
        """Returns the manual's page for a (mostly Debian) linux command."""
        url = f"https://man.cx/{urllib.parse.quote(page.strip(), safe='()')}"

        async with ctx.typing():
            async with self.bot.http_session.get(url) as response:
                if response.status != HTTP_OK:
                    return await ctx.reply(f"An error occurred (status code: {response.status}). Retry later.")
                html = await response.text()

            parsed = await asyncio.to_thread(parse_man_page, html)  # big pages are CPU-heavy

        if parsed is None:
            return await ctx.reply(f"No manual entry for `{page}`. (Debian)")

        view = PaginationView(author=ctx.author, items=build_embeds(parsed, url))
        return await view.start(ctx, allowed_mentions=discord.AllowedMentions.none())

    @commands.command()
    async def ascii(
        self,
        ctx: commands.Context[Bot],
        *,
        text: str = commands.parameter(description="The text to convert."),
    ) -> discord.Message:
        """Returns number representation of characters in text."""

        return await ctx.reply(" ".join([str(ord(letter)) for letter in text]))

    @commands.command()
    async def unascii(
        self,
        ctx: commands.Context[Bot],
        *,
        text: str = commands.parameter(description="The char codes to convert."),
    ) -> discord.Message:
        """Reforms string from char codes."""
        try:
            codes = [chr(int(i)) for i in text.split(" ")]

            return await ctx.reply("".join(codes))
        except ValueError as e:
            error_message = "Invalid character code(s) provided."
            raise commands.BadArgument(error_message) from e

    @commands.command()
    async def byteconvert(
        self,
        ctx: commands.Context[Bot],
        value: int = commands.parameter(description="The value to convert."),
        unit: Literal["o", "kio", "mio", "gio", "tio", "pio", "eio", "zio", "yio"] = commands.parameter(
            description="The unit of the given value.", default="mio"
        ),
    ) -> discord.Message:
        """Shows byte conversions of given value."""
        units = ("o", "kio", "mio", "gio", "tio", "pio", "eio", "zio", "yio")

        emb = discord.Embed(title="Binary conversions")
        index = units.index(unit)

        for i, u in enumerate(units):
            result = round(value / 2 ** ((i - index) * 10), 14)
            emb.add_field(name=u, value=result)

        return await ctx.reply(embed=emb)

    @commands.command(name="hash")
    async def _hash(
        self,
        ctx: commands.Context[Bot],
        algorithm: str = commands.parameter(description="The hashing algorithm to use."),
        *,
        text: str = commands.parameter(description="The text to hash."),
    ) -> discord.Message:
        """Hashes text with a given algorithm UTF-8, returns under hexadecimal form.

        Available algorithms:
        - `md5`
        - `sha1`
        - `sha224`
        - `sha256`
        - `sha384`
        - `sha512`
        - `blake2b`
        - `blake2s`
        """
        algo = algorithm.lower()

        if algo not in self.algos:
            error_message = f"Algorithm `{algorithm}` not found. Available algorithms: `{', '.join(self.algos)}`."
            raise commands.BadArgument(error_message)

        try:
            # Guaranteed one
            hash_object = getattr(hashlib, algo)(text.encode("utf-8"))
        except AttributeError:
            # Available
            hash_object = hashlib.new(algo, text.encode("utf-8"))

        emb = discord.Embed(title=f"{algorithm} hash", description=hash_object.hexdigest()).set_footer(text=f"Invoked by {ctx.message.author!s}")

        return await ctx.reply(embed=emb)

    @commands.command()
    async def charinfo(
        self,
        ctx: commands.Context[Bot],
        *,
        characters: str = commands.parameter(description="The characters to get information about."),
    ) -> discord.Message:
        """Shows you information about a number of characters.

        Only up to 25 characters at a time.
        """

        def to_string(c):
            digit = f"{ord(c):x}"
            name = unicodedata.name(c, "Name not found.")
            return f"`\\U{digit:>08}`: {name} - {c} - <http://www.fileformat.info/info/unicode/char/{digit}>"

        msg = "\n".join(map(to_string, characters))
        if len(msg) > DISCORD_MESSAGE_LIMIT:
            return await ctx.reply("Output too long to display.")
        return await ctx.reply(msg)

    @commands.command(aliases=["rp"])
    @commands.cooldown(1, 10, commands.cooldowns.BucketType.user)
    async def realpython(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="The search terms to look for."),
    ) -> discord.Message:
        """Send some articles from RealPython that match the search terms."""

        MAX_DESCRIPTION_LENGTH = 150

        if not query.strip():
            return await ctx.reply(
                embed=discord.Embed(
                    title="Real Python",
                    url=REAL_PYTHON_BASE_URL,
                    description="Learn Python with tutorials, courses and learning paths.",
                    color=ctx.author.color,
                ),
                mention_author=False,
            )

        params = {"q": query, "limit": 5, "kinds": "article"}
        try:
            async with self.bot.http_session.get(
                REAL_PYTHON_ROOT_API,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                data = await response.json()
        except aiohttp.ClientError, TimeoutError:
            return await ctx.reply(
                embed=discord.Embed(
                    title="Error while searching Real Python",
                    description="There was an error while trying to reach Real Python. Please try again shortly.",
                    color=ctx.author.color,
                ),
                mention_author=False,
            )

        articles = data.get("results", [])
        if not articles:
            return await ctx.reply(
                embed=discord.Embed(title=f"No articles found for '{query}'", color=ctx.author.color),
                mention_author=False,
            )

        total = data.get("total", len(articles))
        embed = discord.Embed(
            title="Search results - Real Python",
            url=REAL_PYTHON_SEARCH_URL.format(query=quote_plus(query)),
            description="Here is the result:" if len(articles) == 1 else f"Here are the top {len(articles)} results:",
            color=ctx.author.color,
        )

        for article in articles:
            link = urljoin(REAL_PYTHON_BASE_URL, article["url"])
            description = truncate(article.get("description") or "", MAX_DESCRIPTION_LENGTH)
            embed.add_field(
                name=truncate(article["title"], 256),
                value=f"{description}\n{link}" if description else link,
                inline=False,
            )

        embed.set_footer(text=f"Showing {len(articles)} of {total} matches. Click the links to read more.")
        return await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=["so"])
    @commands.cooldown(1, 15, commands.cooldowns.BucketType.user)
    async def stackoverflow(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str = commands.parameter(description="The search terms to look for."),
    ) -> discord.Message:
        """Sends the top 5 results of a search query from stackoverflow."""
        params = {**STACKOVERFLOW_PARAMS, "q": query}
        async with self.bot.http_session.get(url=STACKOVERFLOW_BASE_API, params=params) as response:
            if response.status == HTTP_OK:
                data = await response.json()
            else:
                return await ctx.reply(
                    embed=discord.Embed(
                        title="Error in fetching results from Stackoverflow",
                        description=(
                            "Sorry, there was en error while trying to fetch data from the Stackoverflow website. Please try again in some time"
                        ),
                        color=ctx.author.color,
                    )
                )

        if not data["items"]:
            no_search_result = discord.Embed(title=f"No search results found for {query}", color=ctx.author.color)
            return await ctx.reply(embed=no_search_result)

        top5 = data["items"][:5]
        encoded_search_query = quote_plus(query)
        embed = discord.Embed(
            title="Search results - Stackoverflow",
            url=STACKOVERFLOW_SEARCH_URL.format(query=encoded_search_query),
            description=f"Here are the top {len(top5)} results:",
            color=ctx.author.color,
        )
        for item in top5:
            embed.add_field(
                name=unescape(item["title"]),
                value=(
                    f"[\N{UPWARDS BLACK ARROW} {item['score']}  \N{EYES} {item['view_count']}  \N{PAGE FACING UP} {item['answer_count']}  \N{ADMISSION TICKETS} {', '.join(item['tags'][:3])}]({item['link']})"
                ),
                inline=False,
            )
        embed.set_footer(text="View the original link for more results.")
        try:
            return await ctx.reply(embed=embed)
        except discord.HTTPException:
            search_query_too_long = discord.Embed(
                title="Your search query is too long, please try shortening your search query",
                color=ctx.author.color,
            )
            return await ctx.reply(embed=search_query_too_long)

    @commands.group(name="cheat", aliases=["cht.sh", "cheatsheet", "cheat-sheet", "cht"])
    async def cheat_sh(self, ctx: commands.Context[Bot], *search_terms: str) -> discord.Message:
        """Search cheat.sh.

        `cheat tar`                       UNIX/Linux command
        `cheat python reverse a list`     language + query (also `python/lambda`)
        `cheat reverse a list`            language omitted -> python

        Flags: `-q` hide comments, `-n 2` pick the 2nd alternative answer.
        """
        return await self.cheat_repository.cheat_sheet(ctx, *search_terms)

    @cheat_sh.command(name="search", aliases=["find", "s"])
    async def cheat_search(self, ctx: commands.Context, *terms: str) -> None:
        """Keyword search: `cheat search snapshot` or `cheat search python currying`."""

        return await self.cheat_repository.search(ctx, *terms)

    @cheat_sh.command(name="list", aliases=["ls", "topics"])
    async def cheat_list(
        self,
        ctx: commands.Context,
        language: str | None = commands.parameter(default=None, description="Only list topics for this language"),
    ) -> None:
        """List all topics (`cheat list`) or the topics of one language (`cheat list go`)."""

        return await self.cheat_repository.list(ctx, language)

    @cheat_sh.command(name="learn", aliases=["tutorial"])
    async def cheat_learn(
        self,
        ctx: commands.Context,
        language: str = commands.parameter(description="The language to learn"),
    ) -> None:
        """Learn X in Y minutes for a language: `cheat learn rust`."""
        await self.cheat_repository._lang_page(":learn", "learn")(ctx, language)

    @cheat_sh.command(name="hello")
    async def cheat_hello(
        self,
        ctx: commands.Context,
        language: str = commands.parameter(description="The language to get started with"),
    ) -> None:
        """How to get started + Hello World: `cheat hello kotlin`."""
        await self.cheat_repository._lang_page("hello", "hello world")(ctx, language)

    @cheat_sh.command(name="oneliners", aliases=["1line", "oneliner"])
    async def cheat_oneliners(
        self,
        ctx: commands.Context,
        language: str = commands.parameter(description="The language whose one-liners to show"),
    ) -> None:
        """One-liners (perl, python, js): `cheat oneliners perl`."""
        await self.cheat_repository._lang_page("1line", "one-liners")(ctx, language)

    @cheat_sh.command(name="random", aliases=["rand"])
    async def cheat_random(
        self,
        ctx: commands.Context,
        language: str | None = commands.parameter(default=None, description="Only pick from this language"),
    ) -> None:
        """A random cheat sheet, optionally within a language."""

        await self.cheat_repository.random(ctx, language)

    @cheat_sh.command(name="languages", aliases=["langs", "language"])
    async def cheat_languages(self, ctx: commands.Context) -> None:
        """Show supported languages/topics and their aliases."""
        await self.cheat_repository.languages(ctx)

    @commands.command(aliases=["wtfp"])
    async def wtfpython(
        self,
        ctx: commands.Context[Bot],
        *,
        query: str | None = commands.parameter(description="The search terms to look for.", default=None),
    ) -> discord.Message:
        """Search WTF Python repository.
        Gets the link of the fuzzy matched query from https://github.com/satwikkansal/wtfpython.
        """
        if query is None:
            no_query_embed = discord.Embed(
                title="WTF Python?!",
                colour=ctx.author.color,
                description="A repository filled with suprising snippets that can make you say WTF?!",
                url=WTF_PYTHON_BASE_URL,
            )
            return await ctx.reply(embed=no_query_embed)

        fuzzy_match_result = self.wtf_fuzzy_match_header(query)

        if fuzzy_match_result is None:
            error_message = "No matching section found for the given query."
            raise commands.BadArgument(error_message)

        embed = discord.Embed(
            title="WTF Python?!",
            colour=ctx.author.color,
            description=f"""Search result for '{query}': {fuzzy_match_result.split("]")[0].replace("[", "")}
            [Go to Repository Section]({self.wtf_section_links[fuzzy_match_result]})""",
        )
        return await ctx.reply(embed=embed)

    def _format_codeblock(self, content: str, lang: str = "") -> str:
        """Safely wraps output in a codeblock and truncates if over Discord's 2000-char limit."""
        # Prevent breaking out of the codeblock
        safe_content = content.replace("```", "`\u200b``")
        max_len = 1950 - len(lang)
        if len(safe_content) > max_len:
            safe_content = safe_content[:max_len] + "\n... [Output Truncated]"
        return f"```{lang}\n{safe_content}\n```"

    @staticmethod
    def _int_to_base(n: int, base: int) -> str:
        """Converts a base-10 integer to any base between 2 and 36."""
        if n == 0:
            return "0"
        digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        sign = "-" if n < 0 else ""
        n = abs(n)
        result = []
        while n:
            result.append(digits[n % base])
            n //= base
        return sign + "".join(reversed(result))

    @staticmethod
    def _clean_json_input(text: str) -> str:
        """Strips surrounding markdown codeblocks if a user pasted formatted JSON."""
        text = text.strip()
        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            if len(lines) >= 2:
                return "\n".join(lines[1:-1]).strip()
        return text

    async def cog_unload(self) -> None:
        """Unload the cog and cancel the task."""
        if self.fetch_readme.is_running():
            self.fetch_readme.cancel()

        for Cog in DEPENDENCIES:
            await Cog.cog_unload(self)

    @commands.group(name="base64", invoke_without_command=True)
    async def base64_group(self, ctx: commands.Context[Bot]):
        """Encode or decode Base64 strings."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @base64_group.command(name="encode")
    async def base64_encode(self, ctx: commands.Context[Bot], *, text: str = commands.parameter(description="The text to encode into Base64")):
        """Encode plain text into Base64."""
        encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        await ctx.send(self._format_codeblock(encoded))

    @base64_group.command(name="decode")
    async def base64_decode(self, ctx: commands.Context[Bot], *, text: str = commands.parameter(description="The Base64 string to decode")):
        """Decode a Base64 string into plain text."""
        try:
            # Handle missing padding automatically
            padded = text.strip() + "=" * (-len(text.strip()) % 4)
            decoded = base64.b64decode(padded).decode("utf-8")
            await ctx.send(self._format_codeblock(decoded))
        except Exception as e:
            await ctx.send(f"Failed to decode Base64: `{e}`", ephemeral=True)

    @commands.group(name="url", invoke_without_command=True)
    async def url_group(self, ctx: commands.Context[Bot]):
        """Encode or decode URL components."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @url_group.command(name="encode")
    async def url_encode(self, ctx: commands.Context[Bot], *, text: str = commands.parameter(description="The string to URL-encode")):
        """Percent-encode a string for safe inclusion in URLs."""
        encoded = urllib.parse.quote(text, safe="")
        await ctx.send(self._format_codeblock(encoded))

    @url_group.command(name="decode")
    async def url_decode(self, ctx: commands.Context[Bot], *, text: str = commands.parameter(description="The URL-encoded string to decode")):
        """Decode a percent-encoded URL component."""
        decoded = urllib.parse.unquote(text)
        await ctx.send(self._format_codeblock(decoded))

    @commands.command(name="json")
    async def json_cmd(self, ctx: commands.Context[Bot], *, text: str = commands.parameter(description="The JSON string to validate and format")):
        """Validate and pretty-print JSON."""
        cleaned = self._clean_json_input(text)
        try:
            parsed = json.loads(cleaned)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            await ctx.send(self._format_codeblock(formatted, "json"))
        except json.JSONDecodeError as e:
            await ctx.send(
                f"**Invalid JSON:** `{e.msg}` at line `{e.lineno}`, column `{e.colno}`.",
                ephemeral=True,
            )

    @commands.command(name="regex", aliases=["re", "re2"])
    async def regex_cmd(
        self,
        ctx: commands.Context[Bot],
        pattern: str = commands.parameter(description="The regular expression pattern to test."),
        *,
        text: str = commands.parameter(description="The text to test the regex against."),
    ):
        """Test a regular expression against a text block.

        This is not a full regex debugger, it uses google's re2 engine which is safe against catastrophic backtracking.
        Read here: <https://github.com/google/re2>
        """

        def _evaluate_regex():
            matches = list(re2.finditer(pattern, text))
            if not matches:
                return None
            lines = []
            for idx, m in enumerate(matches[:15], 1):
                line = f"{idx}. Match: {m.group(0)!r} (Span: {m.start()}-{m.end()})"
                if m.groups():
                    line += f" | Groups: {m.groups()}"
                if m.groupdict():
                    line += f" | Named: {m.groupdict()}"
                lines.append(line)
            if len(matches) > 15:
                lines.append(f"... and {len(matches) - 15} more matches.")
            return len(matches), "\n".join(lines)

        try:
            # Run with a strict timeout in a separate thread to mitigate catastrophic backtracking (ReDoS)
            result = await asyncio.wait_for(asyncio.to_thread(_evaluate_regex), timeout=2.0)
        except re.error as e:
            await ctx.send(f"**Invalid Regex Pattern:** `{e}`", ephemeral=True)
            return
        except TimeoutError:
            await ctx.send(
                "**Timeout:** Regex evaluation took too long (possible catastrophic backtracking).",
                ephemeral=True,
            )
            return

        if result is None:
            await ctx.send("No matches found.")
        else:
            count, output = result
            await ctx.send(f"Found **{count}** match(es):\n{self._format_codeblock(output, 'py')}")

    @commands.command(name="base")
    async def base_cmd(
        self,
        ctx: commands.Context[Bot],
        number: str,
        from_base: Annotated[int, commands.Range[int, 2, 36]] = commands.parameter(description="Source base (2-36)", displayed_name="from"),
        to_base: Annotated[int, commands.Range[int, 2, 36]] = commands.parameter(description="Target base (2-36)", displayed_name="to"),
    ):
        """Convert a number between bases (supports bases 2 through 36)."""
        try:
            clean_num = number.strip().replace("_", "")
            decimal_val = int(clean_num, from_base)
            converted = self._int_to_base(decimal_val, to_base)
            await ctx.send(f"**Base {from_base}:** `{number}`\n**Base {to_base}:** {self._format_codeblock(converted)}")
        except ValueError:
            await ctx.send(
                f"`{number}` is not a valid integer in base **{from_base}**.",
                ephemeral=True,
            )

    @commands.command(name="escape")
    async def escape_cmd(
        self,
        ctx: commands.Context[Bot],
        fmt: Literal["all", "python", "json", "html"] = commands.parameter(description="The format to escape for (default: all)", default="all"),
        *,
        text: str = commands.parameter(description="The text to escape"),
    ):
        """Escape strings for Python, JSON, or HTML."""
        py_escaped = repr(text)
        json_escaped = json.dumps(text)
        html_escaped = html.escape(text, quote=True)

        if fmt == "python":
            await ctx.send(self._format_codeblock(py_escaped, "py"))
        elif fmt == "json":
            await ctx.send(self._format_codeblock(json_escaped, "json"))
        elif fmt == "html":
            await ctx.send(self._format_codeblock(html_escaped, "html"))
        else:
            output = f"# Python\n{py_escaped}\n\n# JSON\n{json_escaped}\n\n# HTML\n{html_escaped}"
            await ctx.send(self._format_codeblock(output, "py"))

    @commands.command(name="unescape")
    async def unescape_cmd(
        self,
        ctx: commands.Context[Bot],
        *,
        text: str = commands.parameter(description="The escaped string (HTML, JSON, or Python style)"),
    ):
        """Reverse HTML, JSON, or Python string escaping."""
        raw = text.strip()

        # 1. Try JSON string literal if wrapped in double quotes
        if raw.startswith('"') and raw.endswith('"'):
            try:
                res = json.loads(raw)
                if isinstance(res, str):
                    await ctx.send(self._format_codeblock(res))
                    return
            except json.JSONDecodeError:
                pass

        # 2. Try raw JSON escape sequences (e.g. \n, \t, \uXXXX without outer quotes)
        try:
            escaped_quotes = raw.replace('"', '\\"')
            res = json.loads(f'"{escaped_quotes}"')
            if res != raw:
                await ctx.send(self._format_codeblock(res))
                return
        except json.JSONDecodeError:
            pass

        # 3. Fallback to HTML unescaping (&amp;, &#39;, etc.) and unicode_escape
        res = html.unescape(raw)
        if res == raw and "\\" in raw:
            with contextlib.suppress(json.JSONDecodeError):
                res = raw.encode("utf-8").decode("unicode_escape")

        await ctx.send(self._format_codeblock(res))

    async def cog_load(self) -> None:
        """Load the cog and start the task."""
        if self.fetch_readme.is_running():
            self.fetch_readme.restart()
        else:
            self.fetch_readme.start()

        for Cog in DEPENDENCIES:
            await Cog.cog_load(self)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Developer(bot))
