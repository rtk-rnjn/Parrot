from __future__ import annotations

import asyncio
import hashlib
import inspect
import logging
import os
import re
import unicodedata
import urllib.parse
from html import unescape
from typing import TYPE_CHECKING, Annotated, Literal
from urllib.parse import quote_plus

import discord
import rapidfuzz
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from discord.ext import commands, tasks
from jishaku.codeblocks import Codeblock, codeblock_converter

from core.utils import PaginationView

from .cheat_sh import CheatSheet
from .constants import (
    MINIMUM_CERTAINTY,
    REAL_PYTHON_ARTICLE_URL,
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

DEPENDENCIES = [Packages, GitHub, Docs, Kontests, Syntax, Python]


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
        amount: commands.Range[int, 1, 5] = commands.parameter(description="The amount of articles to fetch (1-5).", default=5),  # noqa: B008
        *,
        query: str = commands.parameter(description="The search terms to look for."),
    ) -> discord.Message:
        """Send some articles from RealPython that match the search terms.
        By default the top 5 matches are sent, this can be overwritten to a number between 1 and 5 by specifying an amount before the search query.
        If no search query is specified by the user, the home page is sent.
        """

        params = {"q": query, "limit": amount, "kind": "article"}
        async with self.bot.http_session.get(url=REAL_PYTHON_ROOT_API, params=params) as response:
            if response.status != HTTP_OK:
                return await ctx.reply(
                    embed=discord.Embed(
                        title="Error while searching Real Python",
                        description="There was an error while trying to reach Real Python. Please try again shortly.",
                        color=ctx.author.color,
                    )
                )

            data = await response.json()

        articles = data["results"]

        if len(articles) == 0:
            no_articles = discord.Embed(title=f"No articles found for '{query}'", color=ctx.author.color)
            return await ctx.reply(embed=no_articles)

        article_description = "Here is the result:" if len(articles) == 1 else f"Here are the top {len(articles)} results:"

        article_embed = discord.Embed(
            title="Search results - Real Python",
            url=REAL_PYTHON_SEARCH_URL.format(user_search=quote_plus(query)),
            description=article_description,
            color=ctx.author.color,
        )

        for article in articles:
            article_embed.add_field(
                name=unescape(article["title"]),
                value=REAL_PYTHON_ARTICLE_URL.format(article_url=article["url"]),
                inline=False,
            )
        article_embed.set_footer(text="Click the links to go to the articles.")

        return await ctx.reply(embed=article_embed)

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

    async def cog_unload(self) -> None:
        """Unload the cog and cancel the task."""
        if self.fetch_readme.is_running():
            self.fetch_readme.cancel()

        for Cog in DEPENDENCIES:
            await Cog.cog_unload(self)

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
