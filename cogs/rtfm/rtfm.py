from __future__ import annotations

import asyncio
import hashlib
import inspect
import pathlib
import re
import unicodedata
import urllib.parse
from html import unescape
from random import random
from typing import TYPE_CHECKING, Annotated, Any, Literal
from urllib.parse import quote, quote_plus

import aiohttp
import arrow
import discord
import rapidfuzz
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from discord.ext import commands, tasks
from jishaku.codeblocks import Codeblock, codeblock_converter
from jishaku.paginators import PaginatorEmbedInterface
from rapidfuzz.process import extractOne

from ._kontests import AtCoder, CodeForces, CSAcademy, HackerEarth, HackerRank
from ._used import execute_run
from ._utils import (
    ANSI_RE,
    CHEAT_SH_PYTHON_URL,
    CURL_HEADERS,
    GITHUB_API_URL,
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

try:
    import lxml  # noqa: F401  # pylint: disable=unused-import

    HTML_PARSER = "lxml"
except ImportError:
    HTML_PARSER = "html.parser"

if TYPE_CHECKING:
    import frontmatter

    from core.bot import Parrot


class RTFM(commands.Cog):
    """To test code and check docs. Thanks to https://github.com/FrenchMasterSword/RTFMbot."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.algos = sorted([h for h in hashlib.algorithms_available if h.islower()])
        self.wtf_section_links: dict[str, str] = {}
        self.fetch_readme.start()
        self._python_tags: dict[str, frontmatter.Post] = {}

    @property
    def python_tags(self) -> dict[str, frontmatter.Post]:
        if self._python_tags:
            return self._python_tags

        tags_path = pathlib.Path("assets/python_tags")
        for tag_file in tags_path.glob("*.md"):
            with open(tag_file, encoding="utf-8") as file:
                post = frontmatter.load(file)
                tag_name = tag_file.stem
                self._python_tags[tag_name] = post

        return self._python_tags

    @tasks.loop(minutes=60)
    async def fetch_readme(self) -> None:
        """Gets the content of README.md from the WTF Python Repository."""
        async with self.bot.http_session.get(f"{WTF_PYTHON_RAW_URL}README.md") as resp:
            if resp.status == 200:
                raw = await resp.text()
                self.parse_readme(raw)

    def parse_readme(self, data: str) -> None:
        # Match the start of examples, until the end of the table of contents (toc)
        match = re.search(r"\[👀 Examples\]\(#-examples\)\n([\w\W]*)<!-- tocstop -->", data)
        if not match:
            return
        table_of_contents = match[0].split("\n")

        for header in list(map(str.strip, table_of_contents)):
            if match := re.search(r"\[▶ (.*)\]\((.*)\)", header):
                hyper_link = match[0].split("(")[1].replace(")", "")
                self.wtf_section_links[match[0]] = f"{WTF_PYTHON_BASE_URL}/{hyper_link}"

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
        if len(content) >= 1024:
            content = f"{content[:1021]}..."

        return re.sub(r" +", " ", content)

    @property
    def session(self):
        return self.bot.http_session

    async def get_pypi_package(self, url: str):
        return await self.session.get(url=url)

    @commands.group(name="python-tutorial", aliases=["pytut", "python3-tutorial"], invoke_without_command=True)
    async def python(
        self,
        ctx: commands.Context[Parrot],
        *,
        text: str = commands.parameter(description="The tutorial to search for."),
    ) -> discord.Message:
        """Search for a python tutorial."""
        match = await asyncio.to_thread(extractOne, text, self.python_tags.keys())
        if match is None:
            return await ctx.reply(embed=discord.Embed(description="No such tutorial found in the search query."))

        if match[1] < 50:
            return await ctx.reply(embed=discord.Embed(description="No such tutorial found in the search query."))

        data = self.python_tags[match[0]]
        return await ctx.reply(embed=discord.Embed(description=data.content))

    @python.command(name="list", aliases=["ls", "all"])
    async def python_list(self, ctx: commands.Context[Parrot]) -> discord.Message:
        return await ctx.reply(embed=discord.Embed(title="List of available tutorials", description="`" + "`, `".join(self.python_tags.keys()) + "`"))

    @commands.command(aliases=["pypi"])
    async def pypisearch(
        self,
        ctx: commands.Context[Parrot],
        package: str = commands.parameter(description="The package to search for."),
    ) -> discord.Message:
        """Get info about a Python package directly from PyPi."""
        res_raw = await self.get_pypi_package(f"https://pypi.org/pypi/{package}/json")

        try:
            res_json: dict = await res_raw.json()
        except aiohttp.ContentTypeError as e:
            error_message = f"An error occurred while fetching package data: {str(e)}"
            raise commands.CommandError(error_message) from e

        res = res_json.get("info", "Unknown")

        def getval(key: str):
            return res.get(key, "Unknown")

        name = getval("name")
        author = getval("author")
        author_email = getval("author_email")

        description = getval("summary")
        home_page = getval("home_page")

        project_url = getval("project_url")
        version = getval("version")
        _license = getval("license")

        embed = (
            discord.Embed(title=f"{name} PyPi Stats", description=description, color=discord.Color.teal())
            .add_field(name="Author", value=author, inline=True)
            .add_field(name="Author Email", value=author_email, inline=True)
            .add_field(name="Version", value=version, inline=False)
            .add_field(name="License", value=_license, inline=True)
            .add_field(name="Project Url", value=project_url, inline=False)
            .add_field(name="Home Page", value=home_page)
            .set_thumbnail(url="https://i.imgur.com/syDydkb.png")
        )

        return await ctx.reply(embed=embed)

    @commands.command(aliases=["npm"])
    async def npmsearch(
        self,
        ctx: commands.Context[Parrot],
        package: str = commands.parameter(description="The package to search for."),
    ) -> discord.Message:
        """Get info about a NPM package directly from the NPM Registry."""
        res_raw = await self.get_pypi_package(f"https://registry.npmjs.org/{package}/")

        res_json = await res_raw.json()

        if res_json.get("error"):
            error_message = "NPM package not found."
            raise commands.CommandError(error_message)

        latest_version: str = res_json["dist-tags"]["latest"]
        latest_info: dict = res_json["versions"][latest_version]

        def getval(*keys: str) -> str:
            list_keys = list(keys)
            val: dict = latest_info.get(list_keys.pop(0)) or {}

            result: str | None = None

            for i in list_keys:
                try:
                    result = val.get(i)
                except TypeError:
                    result = "Unknown"

            return result or "Unknown"

        pkg_name = getval("name")
        description = getval("description")

        author = getval("author", "name")
        author_email = getval("author", "email")

        repository = getval("repository", "url").removeprefix("git+").removesuffix(".git")

        homepage = getval("homepage")
        _license = getval("license")

        em = (
            discord.Embed(title=f"{pkg_name} NPM Stats", description=description, color=0xCC3534)
            .add_field(name="Author", value=author, inline=True)
            .add_field(name="Author Email", value=author_email, inline=True)
            .add_field(name="Latest Version", value=latest_version, inline=False)
            .add_field(name="License", value=_license, inline=True)
            .add_field(name="Repository", value=repository, inline=False)
            .add_field(name="Homepage", value=homepage, inline=True)
            .set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Npm-logo.svg/800px-Npm-logo.svg.png")
        )

        return await ctx.reply(embed=em)

    @commands.command(aliases=["crates"])
    async def crate(
        self,
        ctx: commands.Context[Parrot],
        package: str = commands.parameter(description="The package to search for."),
    ) -> discord.Message:
        """Get info about a Rust package directly from the Crates.IO Registry."""
        res_raw = await self.get_pypi_package(f"https://crates.io/api/v1/crates/{package}")

        res_json = await res_raw.json()

        if res_json.get("errors"):
            error_message = "Crate not found."
            raise commands.CommandError(error_message)

        main_info = res_json["crate"]
        latest_info = res_json["versions"][0]

        def getmainval(key):
            return main_info[key] or "Unknown"

        def getversionvals(*keys):
            keys = list(keys)
            val: dict = latest_info.get(keys.pop(0)) or {}

            value = None

            if keys:
                for i in keys:
                    try:
                        value = val.get(i)
                    except TypeError:
                        return "Unknown"

            return value or "Unknown"

        pkg_name = getmainval("name")
        description = getmainval("description")
        downloads = getmainval("downloads")

        publisher = getversionvals("published_by", "name")
        latest_version = getversionvals("num")
        repository = getmainval("repository")

        homepage = getmainval("homepage")
        _license = getversionvals("license")

        em = (
            discord.Embed(title=f"{pkg_name} crates.io Stats", description=description, color=0xE03D29)
            .add_field(name="Published By", value=publisher, inline=True)
            .add_field(name="Downloads", value=f"{downloads:,}", inline=True)
            .add_field(name="Latest Version", value=latest_version, inline=False)
            .add_field(name="License", value=_license, inline=True)
            .add_field(name="Repository", value=repository, inline=False)
            .add_field(name="Homepage", value=homepage, inline=True)
            .set_thumbnail(
                url="https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/Rust_programming_language_black_logo.svg/2048px-Rust_programming_language_black_logo.svg.png",
            )
        )

        return await ctx.reply(embed=em)

    @commands.command()
    async def run(
        self,
        ctx: commands.Context[Parrot],
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
    async def man(self, ctx: commands.Context[Parrot], *, page: str = commands.parameter(description="The manual page to get.")) -> discord.Message:
        """Returns the manual's page for a (mostly Debian) linux command."""
        base_url = f"https://man.cx/{page}"
        url = urllib.parse.quote_plus(base_url, safe=";/?:@&=$,><-[]")

        async with self.bot.http_session.get(url) as response:
            if response.status != 200:
                return await ctx.reply("An error occurred (status code: {response.status}). Retry later.")

            soup = BeautifulSoup(await response.text(), HTML_PARSER)

            name_tag = None
            for tag in soup.find_all("h2"):
                if tag.string and tag.string.strip() == "NAME":
                    name_tag = tag
                    break

            if name_tag is None:
                # No NAME, no page
                return await ctx.reply(f"No manual entry for `{page}`. (Debian)")

            # Get the two (or less) first parts from the nav aside
            # The first one is NAME, we already have it in nameTag
            contents: list[Tag] = soup.find_all("nav", limit=2)[1].find_all("li", limit=3)[1:]

            if contents[-1].string == "COMMENTS":
                contents.remove(-1)

            title = self.get_content(name_tag)

            emb = (
                discord.Embed(title=title, url=f"https://man.cx/{page}")
                .set_author(name="Debian Linux man pages")
                .set_thumbnail(url="https://www.debian.org/logos/openlogo-nd-100.png")
            )

            for tag in contents:
                first_child = next(tag.children, None)
                if first_child is None:
                    h2 = None
                else:
                    href = first_child.get("href")
                    if not href or not href.startswith("#"):
                        h2 = None
                    else:
                        anchor = soup.find(attrs={"name": href[1:]})
                        h2 = anchor.find_parent() if anchor else None

                emb.add_field(name=str(tag.string).strip(), value=(self.get_content(h2)).strip(), inline=False)

            return await ctx.reply(embed=emb)

    @commands.command()
    async def ascii(self, ctx: commands.Context[Parrot], *, text: str = commands.parameter(description="The text to convert.")) -> discord.Message:
        """Returns number representation of characters in text."""

        return await ctx.reply(" ".join([str(ord(letter)) for letter in text]))

    @commands.command()
    async def unascii(
        self,
        ctx: commands.Context[Parrot],
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
        ctx: commands.Context[Parrot],
        value: int = commands.parameter(description="The value to convert."),
        unit: Literal["o", "kio", "mio", "gio", "tio", "pio", "eio", "zio", "yio"] = commands.parameter(
            description="The unit of the given value.",
            default="mio",
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
        ctx: commands.Context[Parrot],
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

        emb = discord.Embed(title=f"{algorithm} hash", description=hash_object.hexdigest()).set_footer(text=f"Invoked by {str(ctx.message.author)}")

        return await ctx.reply(embed=emb)

    @commands.command()
    async def charinfo(
        self,
        ctx: commands.Context[Parrot],
        *,
        characters: str = commands.parameter(description="The characters to get information about."),
    ) -> discord.Message:
        """Shows you information about a number of characters.

        Only up to 25 characters at a time.
        """

        def to_string(c):
            digit = f"{ord(c):x}"
            name = unicodedata.name(c, "Name not found.")
            return f"`\\U{digit:>08}`: {name} - {c} \N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>"

        msg = "\n".join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.reply("Output too long to display.")
        return await ctx.reply(msg)

    async def fetch_data(self, url: str) -> dict[str, Any]:
        """Retrieve data as a dictionary."""
        async with self.bot.http_session.get(url) as r:
            return await r.json()

    @commands.group(name="github", aliases=("gh", "git", "g"))  # Thanks `will.#0021` (211756205721255947)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def github_group(self, ctx: commands.Context[Parrot]) -> discord.Message | None:
        """Commands for finding information related to GitHub."""
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

    @github_group.command(name="user", aliases=("userinfo", "u"))  # Thanks `will.#0021` (211756205721255947)
    async def github_user_info(
        self,
        ctx: commands.Context[Parrot],
        username: str = commands.parameter(description="The GitHub username to fetch information for."),
    ) -> discord.Message:
        """Fetches a user's GitHub information."""
        async with ctx.typing():
            user_data = await self.fetch_data(f"{GITHUB_API_URL}/users/{quote_plus(username)}")

            # User_data will not have a message key if the user exists
            if "message" in user_data:
                embed = discord.Embed(title="404!!", description=f"The profile for `{username}` was not found.", colour=ctx.author.color)

                return await ctx.reply(embed=embed)

            gists = user_data["public_gists"]

            # Forming blog link
            if user_data["blog"].startswith("http"):  # Blog link is complete
                blog = user_data["blog"]
            elif user_data["blog"]:  # Blog exists but the link is not complete
                blog = f"https://{user_data['blog']}"
            else:
                blog = "No website link available"

            embed = (
                discord.Embed(
                    title=f"`{user_data['login']}`'s GitHub profile info",
                    description=(f"```\n{user_data['bio']}\n```\n" if user_data["bio"] else ""),
                    colour=discord.Colour.og_blurple(),
                    url=user_data["html_url"],
                    timestamp=arrow.get(user_data["created_at"]).datetime,
                )
                .set_thumbnail(url=user_data["avatar_url"])
                .set_footer(text="Account created at")
                .add_field(name="Public repos", value=f"[{user_data['public_repos']}]({user_data['html_url']}?tab=repositories)")
                .add_field(name="Website", value=blog)
            )

            if user_data["type"] == "User":
                embed.add_field(name="Followers", value=f"[{user_data['followers']}]({user_data['html_url']}?tab=followers)").add_field(
                    name="Following",
                    value=f"[{user_data['following']}]({user_data['html_url']}?tab=following)",
                )

            if user_data["type"] == "User":
                embed.add_field(name="Gists", value=f"[{gists}](https://gist.github.com/{quote_plus(username, safe='')})")

        return await ctx.reply(embed=embed)

    @github_group.command(name="repository", aliases=("repo", "r"))  # Thanks ``willdn`` (will.#0021 - 211756205721255947)
    async def github_repo_info(self, ctx: commands.Context[Parrot], *repository: str) -> discord.Message:
        """Fetches a repositories' GitHub information.
        The repository should look like `user/reponame` or `user reponame`.
        """
        repo = "/".join(repository)
        if repo.count("/") != 1:
            embed = discord.Embed(
                title="Invalid",
                description="The repository should look like `user/reponame` or `user reponame`.",
                colour=ctx.author.color,
            )

            return await ctx.reply(embed=embed)

        async with ctx.typing():
            repo_data = await self.fetch_data(f"{GITHUB_API_URL}/repos/{quote(repo)}")

            # There won't be a message key if this repo exists
            if "message" in repo_data:
                embed = discord.Embed(title="404", description="The requested repository was not found.", colour=ctx.author.color)

                return await ctx.reply(embed=embed)

        embed = discord.Embed(
            title=repo_data["name"],
            description=repo_data["description"],
            colour=discord.Colour.og_blurple(),
            url=repo_data["html_url"],
        )

        # If it's a fork, then it will have a parent key
        try:
            parent = repo_data["parent"]
            embed.description = f"{embed.description}\n\nForked from [{parent['full_name']}]({parent['html_url']})"

        except KeyError:
            pass

        repo_owner = repo_data["owner"]

        embed.set_author(name=repo_owner["login"], url=repo_owner["html_url"], icon_url=repo_owner["avatar_url"])

        repo_created_at = arrow.get(repo_data["created_at"]).humanize()
        last_pushed = arrow.get(repo_data["pushed_at"]).humanize()

        embed.set_footer(
            text=(
                f"{repo_data['forks_count']} \N{OCR FORK} "
                f"\N{BULLET} {repo_data['stargazers_count']} \N{WHITE MEDIUM STAR} "
                f"\N{BULLET} Created At {repo_created_at} "
                f"\N{BULLET} Last Commit {last_pushed}"
            ),
        )

        return await ctx.reply(embed=embed)

    @commands.command(aliases=["rp"])
    @commands.cooldown(1, 10, commands.cooldowns.BucketType.user)
    async def realpython(
        self,
        ctx: commands.Context[Parrot],
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
            if response.status != 200:
                return await ctx.reply(
                    embed=discord.Embed(
                        title="Error while searching Real Python",
                        description="There was an error while trying to reach Real Python. Please try again shortly.",
                        color=ctx.author.color,
                    ),
                )

            data = await response.json()

        articles = data["results"]

        if len(articles) == 0:
            no_articles = discord.Embed(title=f"No articles found for '{query}'", color=ctx.author.color)
            return await ctx.reply(embed=no_articles)

        if len(articles) == 1:
            article_description = "Here is the result:"
        else:
            article_description = f"Here are the top {len(articles)} results:"

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
        ctx: commands.Context[Parrot],
        *,
        query: str = commands.parameter(description="The search terms to look for."),
    ) -> discord.Message:
        """Sends the top 5 results of a search query from stackoverflow."""
        params = {**STACKOVERFLOW_PARAMS, "q": query}
        async with self.bot.http_session.get(url=STACKOVERFLOW_BASE_API, params=params) as response:
            if response.status == 200:
                data = await response.json()
            else:
                return await ctx.reply(
                    embed=discord.Embed(
                        title="Error in fetching results from Stackoverflow",
                        description=(
                            "Sorry, there was en error while trying to fetch data from the Stackoverflow website. Please try again in some time"
                        ),
                        color=ctx.author.color,
                    ),
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
                    f"[\N{UPWARDS BLACK ARROW} {item['score']}  "
                    f"\N{EYES} {item['view_count']}  "
                    f"\N{PAGE FACING UP} {item['answer_count']}  "
                    f"\N{ADMISSION TICKETS} {', '.join(item['tags'][:3])}]"
                    f"({item['link']})"
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

    @commands.command(name="cheat", aliases=["cht.sh", "cheatsheet", "cheat-sheet", "cht"])
    async def cheat_sheet(self, ctx: commands.Context[Parrot], *search_terms: str) -> discord.Message:
        """Search cheat.sh.

        Gets a post from https://cheat.sh/python/ by default.
        """
        search_string = quote_plus(" ".join(search_terms))

        async with self.bot.http_session.get(CHEAT_SH_PYTHON_URL.format(search=search_string), headers=CURL_HEADERS) as response:
            result = ANSI_RE.sub("", await response.text()).translate(str.maketrans({"`": "\\`"}))

        page = commands.Paginator(prefix="```python", suffix="```", max_size=1980)
        for line in result.splitlines():
            page.add_line(line)

        interface = PaginatorEmbedInterface(ctx.bot, page, owner=ctx.author)
        interface = await interface.send_to(ctx)

        assert interface.message is not None

        return interface.message

    @commands.command(aliases=["wtfp"])
    async def wtfpython(
        self,
        ctx: commands.Context[Parrot],
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
                description=f"A repository filled with suprising snippets that can make you say WTF?!\n\n[Go to the Repository]({WTF_PYTHON_BASE_URL})",
            )
            return await ctx.reply(embed=no_query_embed)

        match = self.wtf_fuzzy_match_header(query)

        if match is None:
            error_message = "No matching section found for the given query."
            raise commands.BadArgument(error_message)

        embed = discord.Embed(
            title="WTF Python?!",
            colour=ctx.author.color,
            description=f"""Search result for '{query}': {match.split("]")[0].replace("[", "")}
            [Go to Repository Section]({self.wtf_section_links[match]})""",
        )
        return await ctx.reply(embed=embed)

    async def cog_unload(self) -> None:
        """Unload the cog and cancel the task."""
        self.fetch_readme.cancel()

    kontests_cache = {}

    @commands.command(name="kontest-reload", hidden=True)
    @commands.is_owner()
    async def kontest_reload(self, ctx: commands.Context[Parrot]) -> None:
        self.kontests_cache.clear()
        await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @commands.command(name="kontests")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def kontests(
        self,
        ctx: commands.Context[Parrot],
        platform: Literal["hackerearth", "hackerrank", "codeforces", "atcoder", "csacademy"] = commands.parameter(
            description="The competitive programming platform to get upcoming contests for.",
        ),
    ) -> discord.Message:
        """Get the upcoming contests on various competitive programming platforms."""

        if random() < 0.1:
            await ctx.reply("From Owner: This command is still in development. Please be patient.")

        mapping = {
            "hackerearth": self.kontest_hackerearth,
            "hackerrank": self.kontest_hackerrank,
            "codeforces": self.kontest_codeforces,
            "atcoder": self.kontest_atcoder,
            "csacademy": self.kontest_csacademy,
        }

        kontests = await mapping[platform]()
        if not kontests:
            await ctx.reply(f"No upcoming contests found for `{platform.capitalize()}`.")

        interface = PaginatorEmbedInterface(ctx.bot, kontests, owner=ctx.author)
        interface = await interface.send_to(ctx)

        assert interface.message is not None

        return interface.message

    async def kontest_hackerearth(self) -> list:
        if "hackerearth" not in self.kontests_cache:
            hackerearth = HackerEarth()
            await hackerearth.fetch(self.bot.http_session)
            self.kontests_cache["hackerearth"] = hackerearth.contests

        contests = self.kontests_cache["hackerearth"]

        return [
            inspect.cleandoc(f"""ID: *{contest.id}* | **[{contest.title}]({contest.url})** | {contest.status}
                {contest.description}
                `Start:` {discord.utils.format_dt(contest.start_time, "R")}
                `End  :` {discord.utils.format_dt(contest.end_time, "R")}""")
            for contest in contests
        ]

    async def kontest_hackerrank(self) -> list:
        if "hackerrank" not in self.kontests_cache:
            hackerrank = HackerRank(self.bot)
            await hackerrank.fetch()
            self.kontests_cache["hackerrank"] = hackerrank.contests

        contests = self.kontests_cache["hackerrank"]
        contests = [c for c in contests if not c.ended]

        return [
            inspect.cleandoc(
                f"""ID: *{contest.id}* | **[{contest.name}]({contest.url})** | {"ENDED" if contest.ended else "UPCOMING/ONGOING"}
                {contest.description}
                `Start:` {discord.utils.format_dt(contest.start_time, "R")}
                `End  :` {discord.utils.format_dt(contest.end_time, "R")}""",
            )
            for contest in contests
        ]

    async def kontest_codeforces(self) -> list:
        if "codeforces" not in self.kontests_cache:
            codeforces = CodeForces()
            await codeforces.fetch(self.bot.http_session)
            self.kontests_cache["codeforces"] = codeforces.contests

        contests = self.kontests_cache["codeforces"]
        contests = [c for c in contests if c.phase != "FINISHED"]

        return [
            inspect.cleandoc(f"""ID: *{contest.id}* | **[{contest.name}]({contest.website_url})** | {contest.phase}
                {contest.description}
                `Start:` {discord.utils.format_dt(contest.start_time, "R") if contest.start_time else "TBA"}
                `Time :` {contest.duration_seconds // 60} Minutes""")
            for contest in contests
        ]

    async def kontest_atcoder(self) -> list:
        if "atcoder" not in self.kontests_cache:
            atcoder = AtCoder()
            await atcoder.fetch(self.bot.http_session)
            await atcoder.get_contests(self.bot.http_session)
            self.kontests_cache["atcoder"] = atcoder.contests

        contests = self.kontests_cache["atcoder"]

        return [
            inspect.cleandoc(f"""**[{contest.name}]({contest.url})**
                `Start:` {discord.utils.format_dt(contest.start_time, "R")}
                `Time :` {contest.duration_minutes} Mins""")
            for contest in contests
        ]

    async def kontest_csacademy(self) -> list:
        if "csacademy" not in self.kontests_cache:
            csacademy = CSAcademy()
            await csacademy.fetch(self.bot.http_session)
            self.kontests_cache["csacademy"] = csacademy.contests

        contests = self.kontests_cache["csacademy"]

        return [
            inspect.cleandoc(f"""ID: NA | **[{contest.name}]({contest.url})**
                {contest.description}
                `Start:` {discord.utils.format_dt(contest.start_time, "R") if contest.start_time else "TBA"}
                `End  :` {discord.utils.format_dt(contest.end_time, "R") if contest.end_time else "TBA"}""")
            for contest in contests
        ]
