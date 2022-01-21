from __future__ import annotations

import unicodedata
import os
import re
import sys
import discord
import aiohttp
import hashlib

from random import choice
import rapidfuzz
from datetime import datetime
from hashlib import algorithms_available as algorithms
from html import unescape
from typing import Optional, Union
import asyncio
import urllib.parse
from urllib.parse import quote, quote_plus

from io import BytesIO

from bs4 import BeautifulSoup
from bs4.element import NavigableString

from core import Parrot, Context, Cog

from discord.ext import commands, tasks
from discord import Embed, Interaction, SelectOption, ui

from . import _ref
from . import _doc

from ._used import typing, get_raw, Refresh, wrapping, prepare_payload, execute_run

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

with open("extra/lang.txt") as f:
    languages = f.read()

GITHUB_API_URL = "https://api.github.com"
API_ROOT_RP = "https://realpython.com/search/api/v1/"
ARTICLE_URL = "https://realpython.com{article_url}"
SEARCH_URL_REAL = "https://realpython.com/search?q={user_search}"
BASE_URL_SO = "https://api.stackexchange.com/2.2/search/advanced"
SO_PARAMS = {"order": "desc", "sort": "activity", "site": "stackoverflow"}
SEARCH_URL_SO = "https://stackoverflow.com/search?q={query}"
URL = "https://cheat.sh/python/{search}"
ESCAPE_TT = str.maketrans({"`": "\\`"})
ANSI_RE = re.compile(r"\x1b\[.*?m")
# We need to pass headers as curl otherwise it would default to aiohttp which would return raw html.
HEADERS = {"User-Agent": "curl/7.68.0"}
ERROR_MESSAGE_CHEAT_SHEET = """
Unknown cheat sheet. Please try to reformulate your query.
**Examples**:
```md
$cht read json
$cht hello world
$cht lambda
```
"""
WTF_PYTHON_RAW_URL = "http://raw.githubusercontent.com/satwikkansal/wtfpython/master/"
BASE_URL = "https://github.com/satwikkansal/wtfpython"
API_ROOT = "https://www.codewars.com/api/v1/code-challenges/{kata_id}"
MINIMUM_CERTAINTY = 55
ERROR_MESSAGE = """
Unknown WTF Python Query. Please try to reformulate your query.
**Examples**:
```md
$wtf wild imports
$wtf subclass
$wtf del
```
"""
TIMEOUT = 120
BOOKMARK_EMOJI = "\N{PUSHPIN}"

MAPPING_OF_KYU = {
    8: 0xDDDBDA,
    7: 0xDDDBDA,
    6: 0xECB613,
    5: 0xECB613,
    4: 0x3C7EBB,
    3: 0x3C7EBB,
    2: 0x866CC7,
    1: 0x866CC7,
}

# Supported languages for a kata on codewars.com
SUPPORTED_LANGUAGES = {
    "stable": [
        "c",
        "c#",
        "c++",
        "clojure",
        "coffeescript",
        "coq",
        "crystal",
        "dart",
        "elixir",
        "f#",
        "go",
        "groovy",
        "haskell",
        "java",
        "javascript",
        "kotlin",
        "lean",
        "lua",
        "nasm",
        "php",
        "python",
        "racket",
        "ruby",
        "rust",
        "scala",
        "shell",
        "sql",
        "swift",
        "typescript",
    ],
    "beta": [
        "agda",
        "bf",
        "cfml",
        "cobol",
        "commonlisp",
        "elm",
        "erlang",
        "factor",
        "forth",
        "fortran",
        "haxe",
        "idris",
        "julia",
        "nim",
        "objective-c",
        "ocaml",
        "pascal",
        "perl",
        "powershell",
        "prolog",
        "purescript",
        "r",
        "raku",
        "reason",
        "solidity",
        "vb.net",
    ],
}


NEGATIVE_REPLIES = ["! YOU DONE? !", "! OK, HERE IS AN ERROR !", "! F. !"]


class Icons:
    bookmark = (
        "https://images-ext-2.discordapp.net/external/zl4oDwcmxUILY7sD9ZWE2fU5R7n6QcxEmPYSE5eddbg/"
        "%3Fv%3D1/https/cdn.discordapp.com/emojis/654080405988966419.png?width=20&height=20"
    )


class InformationDropdown(ui.Select):
    """A dropdown inheriting from ui.Select that allows finding out other information about the kata."""

    def __init__(
        self,
        language_embed: Embed,
        tags_embed: Embed,
        other_info_embed: Embed,
        main_embed: Embed,
    ):
        options = [
            SelectOption(
                label="Main Information",
                description="See the kata's difficulty, description, etc.",
                emoji="\N{EARTH GLOBE AMERICAS}",
            ),
            SelectOption(
                label="Languages",
                description="See what languages this kata supports!",
                emoji="\N{PAGE FACING UP}",
            ),
            SelectOption(
                label="Tags",
                description="See what categories this kata falls under!",
                emoji="\N{ROUND PUSHPIN}",
            ),
            SelectOption(
                label="Other Information",
                description="See how other people performed on this kata and more!",
                emoji="\N{INFORMATION SOURCE}",
            ),
        ]

        # We map the option label to the embed instance so that it can be easily looked up later in O(1)
        self.mapping_of_embeds = {
            "Main Information": main_embed,
            "Languages": language_embed,
            "Tags": tags_embed,
            "Other Information": other_info_embed,
        }

        super().__init__(
            placeholder="See more information regarding this kata",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: Interaction) -> None:
        """Callback for when someone clicks on a dropdown."""
        # Edit the message to the embed selected in the option
        # The `original_message` attribute is set just after the message is sent with the view.
        # The attribute is not set during initialization.
        result_embed = self.mapping_of_embeds[self.values[0]]
        await self.original_message.edit(embed=result_embed)


class WrappedMessageConverter(commands.MessageConverter):
    """A converter that handles embed-suppressed links like <http://example.com>."""

    async def convert(self, ctx: Context, argument: str) -> discord.Message:
        """Wrap the commands.MessageConverter to handle <> delimited message links."""
        # It's possible to wrap a message in [<>] as well, and it's supported because its easy
        if argument.startswith("[") and argument.endswith("]"):
            argument = argument[1:-1]
        if argument.startswith("<") and argument.endswith(">"):
            argument = argument[1:-1]

        return await super().convert(ctx, argument)


class RTFM(Cog):
    """To test code and check docs. Thanks to https://github.com/FrenchMasterSword/RTFMbot"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.algos = sorted([h for h in hashlib.algorithms_available if h.islower()])

        self.bot.languages = ()
        self.headers: dict[str, str] = {}
        self.fetch_readme.start()

    @tasks.loop(minutes=60)
    async def fetch_readme(self) -> None:
        """Gets the content of README.md from the WTF Python Repository."""
        async with self.bot.http_session.get(f"{WTF_PYTHON_RAW_URL}README.md") as resp:
            if resp.status == 200:
                raw = await resp.text()
                self.parse_readme(raw)

    @staticmethod
    def build_bookmark_dm(target_message: discord.Message, title: str) -> discord.Embed:
        """Build the embed to DM the bookmark requester."""
        embed = discord.Embed(
            title=title,
            description=target_message.content,
        )
        embed.add_field(
            name="Wanna give it a visit?",
            value=f"[Visit original message]({target_message.jump_url})",
        )
        embed.set_author(
            name=target_message.author,
            icon_url=target_message.author.display_avatar.url,
        )
        embed.set_thumbnail(url=Icons.bookmark)

        return embed

    @staticmethod
    def build_error_embed(user: discord.Member) -> discord.Embed:
        """Builds an error embed for when a bookmark requester has DMs disabled."""
        return discord.Embed(
            title="You DM(s) are closed!",
            description=f"{user.mention}, please enable your DMs to receive the bookmark.",
        )

    async def action_bookmark(
        self,
        channel: discord.TextChannel,
        user: discord.Member,
        target_message: discord.Message,
        title: str,
    ) -> None:
        """Sends the bookmark DM, or sends an error embed when a user bookmarks a message."""
        try:
            embed = self.build_bookmark_dm(target_message, title)
            await user.send(embed=embed)
        except discord.Forbidden:
            error_embed = self.build_error_embed(user)
            await channel.send(embed=error_embed)

    @staticmethod
    async def send_reaction_embed(
        channel: discord.TextChannel, target_message: discord.Message
    ) -> discord.Message:
        """Sends an embed, with a reaction, so users can react to bookmark the message too."""
        message = await channel.send(
            embed=discord.Embed(
                description=(
                    f"React with {BOOKMARK_EMOJI} to be sent your very own bookmark to "
                    f"[this message]({target_message.jump_url})."
                ),
            )
        )

        await message.add_reaction(BOOKMARK_EMOJI)
        return message

    def parse_readme(self, data: str) -> None:
        # Match the start of examples, until the end of the table of contents (toc)
        table_of_contents = re.search(
            r"\[👀 Examples\]\(#-examples\)\n([\w\W]*)<!-- tocstop -->", data
        )[0].split("\n")

        for header in list(map(str.strip, table_of_contents)):
            match = re.search(r"\[▶ (.*)\]\((.*)\)", header)
            if match:
                hyper_link = match[0].split("(")[1].replace(")", "")
                self.headers[match[0]] = f"{BASE_URL}/{hyper_link}"

    def fuzzy_match_header(self, query: str) -> Optional[str]:
        match, certainty, _ = rapidfuzz.process.extractOne(query, self.headers.keys())
        return match if certainty > MINIMUM_CERTAINTY else None

    def get_content(self, tag):
        """Returns content between two h2 tags"""
        bssiblings = tag.next_siblings
        siblings = []
        for elem in bssiblings:
            # get only tag elements, before the next h2
            # Putting away the comments, we know there's
            # at least one after it.
            if type(elem) is NavigableString:
                continue
            # It's a tag
            if elem.name == "h2":
                break
            siblings.append(elem.text)
        content = "\n".join(siblings)
        if len(content) >= 1024:
            content = content[:1021] + "..."

        return content

    referred = {
        "csp-directives": _ref.csp_directives,
        "git": _ref.git_ref,
        "git-guides": _ref.git_tutorial_ref,
        "haskell": _ref.haskell_ref,
        "html5": _ref.html_ref,
        "http-headers": _ref.http_headers,
        "http-methods": _ref.http_methods,
        "http-status-codes": _ref.http_status,
        "sql": _ref.sql_ref,
    }

    # TODO: lua, java, javascript, asm
    documented = {
        "c": _doc.c_doc,
        "cpp": _doc.cpp_doc,
        "haskell": _doc.haskell_doc,
        "python": _doc.python_doc,
    }

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="rtfm", id=893097656375722024)

    @property
    def session(self):
        return self.bot.session

    @staticmethod
    def fmt_error_embed() -> discord.Embed:
        """
        Format the Error Embed.
        If the cht.sh search returned 404, overwrite it to send a custom error embed.
        link -> https://github.com/chubin/cheat.sh/issues/198
        """
        embed = discord.Embed(
            title="! You done? !",
            description=ERROR_MESSAGE_CHEAT_SHEET,
        )
        return embed

    def result_fmt(
        self, url: str, body_text: str
    ) -> tuple[bool, Union[str, discord.Embed]]:
        """Format Result."""
        if body_text.startswith("#  404 NOT FOUND"):
            embed = self.fmt_error_embed()
            return True, embed

        body_space = min(1986 - len(url), 1000)

        if len(body_text) > body_space:
            description = (
                f"**Result Of cht.sh**\n"
                f"```python\n{body_text[:body_space]}\n"
                f"... (truncated - too many lines)\n```\n"
                f"Full results: {url} "
            )
        else:
            description = (
                f"**Result Of cht.sh**\n" f"```python\n{body_text}\n```\n" f"{url}"
            )
        return False, description

    async def get_package(self, url: str):
        return await self.session.get(url=url)

    @commands.command(aliases=["pypi"])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def pypisearch(self, ctx: Context, arg: str):
        """Get info about a Python package directly from PyPi"""
        res_raw = await self.get_package(f"https://pypi.org/pypi/{arg}/json")

        try:
            res_json = await res_raw.json()
        except aiohttp.ContentTypeError:
            return await ctx.send(
                embed=discord.Embed(
                    description="No such package found in the search query.",
                    color=self.bot.color,
                )
            )

        res = res_json["info"]

        def getval(key):
            return res[key] or "Unknown"

        name = getval("name")
        author = getval("author")
        author_email = getval("author_email")

        description = getval("summary")
        home_page = getval("home_page")

        project_url = getval("project_url")
        version = getval("version")
        _license = getval("license")

        embed = discord.Embed(
            title=f"{name} PyPi Stats",
            description=description,
            color=discord.Color.teal(),
        )

        embed.add_field(name="Author", value=author, inline=True)
        embed.add_field(name="Author Email", value=author_email, inline=True)

        embed.add_field(name="Version", value=version, inline=False)
        embed.add_field(name="License", value=_license, inline=True)

        embed.add_field(name="Project Url", value=project_url, inline=False)
        embed.add_field(name="Home Page", value=home_page)

        embed.set_thumbnail(url="https://i.imgur.com/syDydkb.png")

        await ctx.send(embed=embed)

    @commands.command(aliases=["npm"])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def npmsearch(self, ctx: Context, arg: str):
        """Get info about a NPM package directly from the NPM Registry"""
        res_raw = await self.get_package(f"https://registry.npmjs.org/{arg}/")

        res_json = await res_raw.json()

        if res_json.get("error"):
            return await ctx.send(
                embed=discord.Embed(
                    description="No such package found in the search query.",
                    color=0xCC3534,
                )
            )

        latest_version = res_json["dist-tags"]["latest"]
        latest_info = res_json["versions"][latest_version]

        def getval(*keys):
            keys = list(keys)
            val = latest_info.get(keys.pop(0)) or {}

            if keys:
                for i in keys:
                    try:
                        val = val.get(i)
                    except TypeError:
                        return "Unknown"

            return val or "Unknown"

        pkg_name = getval("name")
        description = getval("description")

        author = getval("author", "name")
        author_email = getval("author", "email")

        repository = (
            getval("repository", "url").removeprefix("git+").removesuffix(".git")
        )

        homepage = getval("homepage")
        _license = getval("license")

        em = discord.Embed(
            title=f"{pkg_name} NPM Stats", description=description, color=0xCC3534
        )

        em.add_field(name="Author", value=author, inline=True)
        em.add_field(name="Author Email", value=author_email, inline=True)

        em.add_field(name="Latest Version", value=latest_version, inline=False)
        em.add_field(name="License", value=_license, inline=True)

        em.add_field(name="Repository", value=repository, inline=False)
        em.add_field(name="Homepage", value=homepage, inline=True)

        em.set_thumbnail(
            url="https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Npm-logo.svg/800px-Npm-logo.svg.png"
        )

        await ctx.send(embed=em)

    @commands.command(aliases=["crates"])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def crate(self, ctx: Context, arg: str):
        """Get info about a Rust package directly from the Crates.IO Registry"""
        res_raw = await self.get_package(f"https://crates.io/api/v1/crates/{arg}")

        res_json = await res_raw.json()

        if res_json.get("errors"):
            return await ctx.send(
                embed=discord.Embed(
                    description="No such package found in the search query.",
                    color=0xE03D29,
                )
            )
        main_info = res_json["crate"]
        latest_info = res_json["versions"][0]

        def getmainval(key):
            return main_info[key] or "Unknown"

        def getversionvals(*keys):
            keys = list(keys)
            val = latest_info.get(keys.pop(0)) or {}

            if keys:
                for i in keys:
                    try:
                        val = val.get(i)
                    except TypeError:
                        return "Unknown"

            return val or "Unknown"

        pkg_name = getmainval("name")
        description = getmainval("description")
        downloads = getmainval("downloads")

        publisher = getversionvals("published_by", "name")
        latest_version = getversionvals("num")
        repository = getmainval("repository")

        homepage = getmainval("homepage")
        _license = getversionvals("license")

        em = discord.Embed(
            title=f"{pkg_name} crates.io Stats", description=description, color=0xE03D29
        )

        em.add_field(name="Published By", value=publisher, inline=True)
        em.add_field(name="Downloads", value="{:,}".format(downloads), inline=True)

        em.add_field(name="Latest Version", value=latest_version, inline=False)
        em.add_field(name="License", value=_license, inline=True)

        em.add_field(name="Repository", value=repository, inline=False)
        em.add_field(name="Homepage", value=homepage, inline=True)

        em.set_thumbnail(
            url="https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/Rust_programming_language_black_logo.svg/2048px-Rust_programming_language_black_logo.svg.png"
        )

        await ctx.send(embed=em)

    @commands.command(
        help="""$run <language> [--wrapped] [--stats] <code>
for command-line-options, compiler-flags and arguments you may add a line starting with this argument, and after a space add your options, flags or args.
stats option displays more informations on execution consumption
wrapped allows you to not put main function in some languages, which you can see in `list wrapped argument`
<code> may be normal code, but also an attached file, or a link from [hastebin](https://hastebin.com) or [Github gist](https://gist.github.com)
If you use a link, your command must end with this syntax:
`link=<link>` (no space around `=`)
for instance : `do run python link=https://hastebin.com/resopedahe.py`
The link may be the raw version, and with/without the file extension
If the output exceeds 40 lines or Discord max message length, it will be put
in a new hastebin and the link will be returned.
When the code returns your output, you may delete it by clicking :wastebasket: in the following minute.
Useful to hide your syntax fails or when you forgot to print the result.""",
        brief="Execute code in a given programming language",
    )
    async def run(self, ctx, *, payload=""):
        """Execute code in a given programming language"""
        if not payload:
            emb = discord.Embed(
                title="SyntaxError",
                description="Command `run` missing a required argument: `language`",
                colour=0xFF0000,
            )
            return await ctx.send(embed=emb)

        no_rerun = True
        language = payload
        lang = None  # to override in 2 first cases

        if ctx.message.attachments:
            file = ctx.message.attachments[0]
            if file.size > 20000:
                return await ctx.send("File must be smaller than 20 kio.")
            buffer = BytesIO()
            await ctx.message.attachments[0].save(buffer)
            text = buffer.read().decode("utf-8")
            lang = re.split(r"\s+", payload, maxsplit=1)[0]
        elif payload.split(" ")[-1].startswith("link="):
            # Code in a webpage
            base_url = urllib.parse.quote_plus(
                payload.split(" ")[-1][5:].strip("/"), safe=";/?:@&=$,><-[]"
            )

            url = get_raw(base_url)

            async with self.bot.session.get(url) as response:
                if response.status == 404:
                    return await ctx.send("Nothing found. Check your link")
                if response.status != 200:
                    return await ctx.send(
                        f"An error occurred (status code: {response.status}). Retry later."
                    )
                text = await response.text()
                if len(text) > 20000:
                    return await ctx.send(
                        "Code must be shorter than 20,000 characters."
                    )
                lang = re.split(r"\s+", payload, maxsplit=1)[0]
        else:
            no_rerun = False

            language, text, errored = prepare_payload(
                payload
            )  # we call it text but it's an embed if it errored #JustDynamicTypingThings

            if errored:
                return await ctx.send(embed=text)

        async with ctx.typing():
            if lang:
                language = lang

            output = await execute_run(self.bot, language, text)

            view = Refresh(self.bot, no_rerun)

            try:
                returned = await ctx.reply(output, view=view)
                buttons = True
            except discord.HTTPException:  # message deleted
                returned = await ctx.send(output, view=view)
                buttons = False

        if buttons:

            await view.wait()

            try:
                await returned.edit(view=None)
                view.stop()
            except Exception:
                # We deleted the message
                pass

    @commands.command(aliases=["ref"])
    @commands.bot_has_permissions(embed_links=True)
    @typing
    async def reference(self, ctx: Context, language, *, query: str):
        """Returns element reference from given language"""
        lang = language.strip("`")

        if not lang.lower() in self.referred:
            return await ctx.reply(
                f"{lang} not available. See `[p]list references` for available ones."
            )
        await self.referred[lang.lower()](ctx, query.strip("`"))

    @commands.command(aliases=["doc"])
    @commands.bot_has_permissions(embed_links=True)
    @typing
    async def documentation(self, ctx: Context, language, *, query: str):
        """Returns element reference from given language"""
        lang = language.strip("`")

        if not lang.lower() in self.documented:
            return await ctx.reply(
                f"{lang} not available. See `{ctx.prefix}list documentations` for available ones."
            )
        await self.documented[lang.lower()](ctx, query.strip("`"))

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @typing
    async def man(self, ctx: Context, *, page: str):
        """Returns the manual's page for a (mostly Debian) linux command"""
        base_url = f"https://man.cx/{page}"
        url = urllib.parse.quote_plus(base_url, safe=";/?:@&=$,><-[]")

        async with aiohttp.ClientSession() as client_session:
            async with client_session.get(url) as response:
                if response.status != 200:
                    return await ctx.reply(
                        "An error occurred (status code: {response.status}). Retry later."
                    )

                soup = BeautifulSoup(await response.text(), "lxml")

                nameTag = soup.find("h2", string="NAME\n")

                if not nameTag:
                    # No NAME, no page
                    return await ctx.reply(f"No manual entry for `{page}`. (Debian)")

                # Get the two (or less) first parts from the nav aside
                # The first one is NAME, we already have it in nameTag
                contents = soup.find_all("nav", limit=2)[1].find_all("li", limit=3)[1:]

                if contents[-1].string == "COMMENTS":
                    contents.remove(-1)

                title = self.get_content(nameTag)

                emb = discord.Embed(title=title, url=f"https://man.cx/{page}")
                emb.set_author(name="Debian Linux man pages")
                emb.set_thumbnail(
                    url="https://www.debian.org/logos/openlogo-nd-100.png"
                )

                for tag in contents:
                    h2 = tuple(
                        soup.find(
                            attrs={"name": tuple(tag.children)[0].get("href")[1:]}
                        ).parents
                    )[0]
                    emb.add_field(name=tag.string, value=self.get_content(h2))

                await ctx.reply(embed=emb)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def list(self, ctx: Context, *, group=None):
        """Lists available choices for other commands"""
        choices = {
            "documentations": self.documented,
            "hashing": sorted([h for h in algorithms if h.islower()]),
            "references": self.referred,
            "wrapped argument": wrapping,
        }

        if group == "languages":
            emb = discord.Embed(
                title=f"Available for {group}:",
                description="View them on [tio.run](https://tio.run/#), or in [JSON format](https://tio.run/languages.json)",
            )
            return await ctx.reply(embed=emb)

        if not group in choices:
            emb = discord.Embed(
                title="Available listed commands",
                description=f"`languages`, `{'`, `'.join(choices)}`",
            )
            return await ctx.reply(embed=emb)

        availables = choices[group]
        description = f"`{'`, `'.join([*availables])}`"
        emb = discord.Embed(
            title=f"Available for {group}: {len(availables)}", description=description
        )
        await ctx.reply(embed=emb)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def ascii(self, ctx: Context, *, text: str):
        """Returns number representation of characters in text"""
        emb = discord.Embed(
            title="Unicode convert",
            description=" ".join([str(ord(letter)) for letter in text]),
        )
        emb.set_footer(text=f"Invoked by {str(ctx.message.author)}")
        await ctx.reply(embed=emb)

    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def unascii(self, ctx: Context, *, text: str):
        """Reforms string from char codes"""
        try:
            codes = [chr(int(i)) for i in text.split(" ")]
            emb = discord.Embed(title="Unicode convert", description="".join(codes))
            emb.set_footer(text=f"Invoked by {str(ctx.message.author)}")
            await ctx.reply(embed=emb)
        except ValueError:
            await ctx.reply(
                "Invalid sequence. Example usage : `[p]unascii 104 101 121`"
            )

    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def byteconvert(self, ctx: Context, value: int, unit=None):
        """Shows byte conversions of given value"""
        if not unit:
            unit = "Mio"
        units = ("O", "Kio", "Mio", "Gio", "Tio", "Pio", "Eio", "Zio", "Yio")
        unit = unit.capitalize()

        if unit not in units:
            return await ctx.reply(f"Available units are `{'`, `'.join(units)}`.")

        emb = discord.Embed(title="Binary conversions")
        index = units.index(unit)

        for i, u in enumerate(units):
            result = round(value / 2 ** ((i - index) * 10), 14)
            emb.add_field(name=u, value=result)

        await ctx.reply(embed=emb)

    @commands.command(name="hash")
    @commands.bot_has_permissions(embed_links=True)
    async def _hash(self, ctx: Context, algorithm, *, text: str):
        """
        Hashes text with a given algorithm
        UTF-8, returns under hexadecimal form
        """
        algo = algorithm.lower()

        if not algo in self.algos:
            matches = "\n".join(
                [supported for supported in self.algos if algo in supported][:10]
            )
            message = f"`{algorithm}` not available."
            if matches:
                message += f" Did you mean:\n{matches}"
            return await ctx.reply(message)

        try:
            # Guaranteed one
            hash_object = getattr(hashlib, algo)(text.encode("utf-8"))
        except AttributeError:
            # Available
            hash_object = hashlib.new(algo, text.encode("utf-8"))

        emb = discord.Embed(
            title=f"{algorithm} hash", description=hash_object.hexdigest()
        )
        emb.set_footer(text=f"Invoked by {str(ctx.message.author)}")

        await ctx.reply(embed=emb)

    @commands.command()
    async def charinfo(self, ctx, *, characters: str):
        """Shows you information about a number of characters.
        Only up to 25 characters at a time."""

        def to_string(c):
            digit = f"{ord(c):x}"
            name = unicodedata.name(c, "Name not found.")
            return f"`\\U{digit:>08}`: {name} - {c} \N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>"

        msg = "\n".join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.send("Output too long to display.")
        await ctx.send(msg)

    async def fetch_data(self, url: str) -> dict:
        """Retrieve data as a dictionary."""
        async with self.bot.http_session.get(url) as r:
            return await r.json()

    @commands.group(name="github", aliases=("gh", "git"))
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def github_group(self, ctx: Context) -> None:
        """Commands for finding information related to GitHub."""
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)

    @github_group.command(name="user", aliases=("userinfo",))
    async def github_user_info(self, ctx: Context, username: str) -> None:
        """Fetches a user's GitHub information."""
        async with ctx.typing():
            user_data = await self.fetch_data(
                f"{GITHUB_API_URL}/users/{quote_plus(username)}"
            )

            # User_data will not have a message key if the user exists
            if "message" in user_data:
                embed = discord.Embed(
                    title="404!!",
                    description=f"The profile for `{username}` was not found.",
                    colour=ctx.author.color,
                )

                await ctx.send(embed=embed)
                return

            org_data = await self.fetch_data(user_data["organizations_url"])
            orgs = [
                f"[{org['login']}](https://github.com/{org['login']})"
                for org in org_data
            ]
            orgs_to_add = " | ".join(orgs)

            gists = user_data["public_gists"]

            # Forming blog link
            if user_data["blog"].startswith("http"):  # Blog link is complete
                blog = user_data["blog"]
            elif user_data["blog"]:  # Blog exists but the link is not complete
                blog = f"https://{user_data['blog']}"
            else:
                blog = "No website link available"

            embed = discord.Embed(
                title=f"`{user_data['login']}`'s GitHub profile info",
                description=f"```\n{user_data['bio']}\n```\n"
                if user_data["bio"]
                else "",
                colour=discord.Colour.og_blurple(),
                url=user_data["html_url"],
                timestamp=datetime.strptime(
                    user_data["created_at"], "%Y-%m-%dT%H:%M:%SZ"
                ),
            )
            embed.set_thumbnail(url=user_data["avatar_url"])
            embed.set_footer(text="Account created at")

            if user_data["type"] == "User":

                embed.add_field(
                    name="Followers",
                    value=f"[{user_data['followers']}]({user_data['html_url']}?tab=followers)",
                )
                embed.add_field(
                    name="Following",
                    value=f"[{user_data['following']}]({user_data['html_url']}?tab=following)",
                )

            embed.add_field(
                name="Public repos",
                value=f"[{user_data['public_repos']}]({user_data['html_url']}?tab=repositories)",
            )

            if user_data["type"] == "User":
                embed.add_field(
                    name="Gists",
                    value=f"[{gists}](https://gist.github.com/{quote_plus(username, safe='')})",
                )

                embed.add_field(
                    name=f"Organization{'s' if len(orgs)!=1 else ''}",
                    value=orgs_to_add if orgs else "No organizations.",
                )
            embed.add_field(name="Website", value=blog)

        await ctx.send(embed=embed)

    @github_group.command(name="repository", aliases=("repo",))
    async def github_repo_info(self, ctx: Context, *repo: str) -> None:
        """
        Fetches a repositories' GitHub information.
        The repository should look like `user/reponame` or `user reponame`.
        """
        repo = "/".join(repo)
        if repo.count("/") != 1:
            embed = discord.Embed(
                title="Invalid",
                description="The repository should look like `user/reponame` or `user reponame`.",
                colour=ctx.author.color,
            )

            await ctx.send(embed=embed)
            return

        async with ctx.typing():
            repo_data = await self.fetch_data(f"{GITHUB_API_URL}/repos/{quote(repo)}")

            # There won't be a message key if this repo exists
            if "message" in repo_data:
                embed = discord.Embed(
                    title="404",
                    description="The requested repository was not found.",
                    colour=ctx.author.color,
                )

                await ctx.send(embed=embed)
                return

        embed = discord.Embed(
            title=repo_data["name"],
            description=repo_data["description"],
            colour=discord.Colour.og_blurple(),
            url=repo_data["html_url"],
        )

        # If it's a fork, then it will have a parent key
        try:
            parent = repo_data["parent"]
            embed.description += (
                f"\n\nForked from [{parent['full_name']}]({parent['html_url']})"
            )
        except KeyError:
            pass

        repo_owner = repo_data["owner"]

        embed.set_author(
            name=repo_owner["login"],
            url=repo_owner["html_url"],
            icon_url=repo_owner["avatar_url"],
        )

        repo_created_at = datetime.strptime(
            repo_data["created_at"], "%Y-%m-%dT%H:%M:%SZ"
        ).strftime("%d/%m/%Y")
        last_pushed = datetime.strptime(
            repo_data["pushed_at"], "%Y-%m-%dT%H:%M:%SZ"
        ).strftime("%d/%m/%Y at %H:%M")

        embed.set_footer(
            text=(
                f"{repo_data['forks_count']} \N{OCR FORK} "
                f"\N{BULLET} {repo_data['stargazers_count']} \N{WHITE MEDIUM STAR} "
                f"\N{BULLET} Created At {repo_created_at} "
                f"\N{BULLET} Last Commit {last_pushed}"
            )
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=["rp"])
    @commands.cooldown(1, 10, commands.cooldowns.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def realpython(
        self, ctx: Context, amount: Optional[int] = 5, *, user_search: str
    ) -> None:
        """
        Send some articles from RealPython that match the search terms.
        By default the top 5 matches are sent, this can be overwritten to
        a number between 1 and 5 by specifying an amount before the search query.
        """
        if not 1 <= amount <= 5:
            await ctx.send(
                f"{ctx.author.mention} `amount` must be between 1 and 5 (inclusive)."
            )
            return

        params = {"q": user_search, "limit": amount, "kind": "article"}
        async with self.bot.http_session.get(
            url=API_ROOT_RP, params=params
        ) as response:
            if response.status != 200:
                await ctx.send(
                    embed=discord.Embed(
                        title="Error while searching Real Python",
                        description="There was an error while trying to reach Real Python. Please try again shortly.",
                        color=ctx.author.color,
                    )
                )
                return

            data = await response.json()

        articles = data["results"]

        if len(articles) == 0:
            no_articles = discord.Embed(
                title=f"No articles found for '{user_search}'", color=ctx.author.color
            )
            await ctx.send(embed=no_articles)
            return

        if len(articles) == 1:
            article_description = "Here is the result:"
        else:
            article_description = f"Here are the top {len(articles)} results:"

        article_embed = discord.Embed(
            title="Search results - Real Python",
            url=SEARCH_URL_REAL.format(user_search=quote_plus(user_search)),
            description=article_description,
            color=ctx.author.color,
        )

        for article in articles:
            article_embed.add_field(
                name=unescape(article["title"]),
                value=ARTICLE_URL.format(article_url=article["url"]),
                inline=False,
            )
        article_embed.set_footer(text="Click the links to go to the articles.")

        await ctx.send(embed=article_embed)

    @commands.command(aliases=["so"])
    @commands.cooldown(1, 15, commands.cooldowns.BucketType.user)
    @commands.bot_has_permissions(embed_links=True)
    async def stackoverflow(self, ctx: Context, *, search_query: str) -> None:
        """Sends the top 5 results of a search query from stackoverflow."""
        params = SO_PARAMS | {"q": search_query}
        async with self.bot.http_session.get(
            url=BASE_URL_SO, params=params
        ) as response:
            if response.status == 200:
                data = await response.json()
            else:
                await ctx.send(
                    embed=discord.Embed(
                        title="Error in fetching results from Stackoverflow",
                        description=(
                            "Sorry, there was en error while trying to fetch data from the Stackoverflow website. Please try again in some time"
                        ),
                        color=ctx.author.color,
                    )
                )
                return
        if not data["items"]:
            no_search_result = discord.Embed(
                title=f"No search results found for {search_query}",
                color=ctx.author.color,
            )
            await ctx.send(embed=no_search_result)
            return

        top5 = data["items"][:5]
        encoded_search_query = quote_plus(search_query)
        embed = discord.Embed(
            title="Search results - Stackoverflow",
            url=SEARCH_URL_SO.format(query=encoded_search_query),
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
            await ctx.send(embed=embed)
        except discord.HTTPException:
            search_query_too_long = discord.Embed(
                title="Your search query is too long, please try shortening your search query",
                color=ctx.author.color,
            )
            await ctx.send(embed=search_query_too_long)

    @commands.command(
        name="cheat",
        aliases=["cht.sh", "cheatsheet", "cheat-sheet", "cht"],
    )
    @commands.bot_has_permissions(embed_links=True)
    async def cheat_sheet(self, ctx: Context, *search_terms: str) -> None:
        """
        Search cheat.sh.
        Gets a post from https://cheat.sh/python/ by default.
        Usage:
        --> $cht read json
        """
        async with ctx.typing():
            search_string = quote_plus(" ".join(search_terms))

            async with self.bot.http_session.get(
                URL.format(
                    search=search_string,
                ),
                headers=HEADERS,
            ) as response:
                result = ANSI_RE.sub("", await response.text()).translate(ESCAPE_TT)

            is_embed, description = self.result_fmt(
                URL.format(
                    search=search_string,
                ),
                result,
            )
            if is_embed:
                await ctx.send(embed=description)
            else:
                await ctx.send(content=description)

    @commands.command(aliases=["wtfp"])
    @commands.bot_has_permissions(embed_links=True)
    async def wtfpython(self, ctx: Context, *, query: Optional[str] = None) -> None:
        """
        Search WTF Python repository.
        Gets the link of the fuzzy matched query from https://github.com/satwikkansal/wtfpython.
        Usage:
            --> $wtfp wild imports
        """
        if query is None:
            no_query_embed = discord.Embed(
                title="WTF Python?!",
                colour=ctx.author.color,
                description="A repository filled with suprising snippets that can make you say WTF?!\n\n"
                f"[Go to the Repository]({BASE_URL})",
            )
            await ctx.send(
                embed=no_query_embed,
            )
            return

        if len(query) > 50:
            embed = discord.Embed(
                title="! Well !", description=ERROR_MESSAGE, colour=ctx.author.color
            )
            match = None
        else:
            match = self.fuzzy_match_header(query)

        if not match:
            embed = discord.Embed(
                title="! You done? !",
                description=ERROR_MESSAGE,
                colour=ctx.author.color,
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="WTF Python?!",
            colour=ctx.author.color,
            description=f"""Search result for '{query}': {match.split("]")[0].replace("[", "")}
            [Go to Repository Section]({self.headers[match]})""",
        )
        await ctx.send(
            embed=embed,
        )

    def cog_unload(self) -> None:
        """Unload the cog and cancel the task."""
        self.fetch_readme.cancel()

    @commands.command(name="bookmark", aliases=("bm", "pin"))
    async def bookmark(
        self,
        ctx: Context,
        target_message: Optional[WrappedMessageConverter],
        *,
        title: str = "Bookmark",
    ) -> None:
        """Send the author a link to `target_message` via DMs."""
        if not target_message:
            if not ctx.message.reference:
                raise commands.BadArgument(
                    "You must either provide a valid message to bookmark, or reply to one."
                    "\n\nThe lookup strategy for a message is as follows (in order):"
                    "\n1. Lookup by '{channel ID}-{message ID}' (retrieved by shift-clicking on 'Copy ID')"
                    "\n2. Lookup by message ID (the message **must** be in the context channel)"
                    "\n3. Lookup by message URL"
                )
            target_message = ctx.message.reference.resolved

        # Prevent users from bookmarking a message in a channel they don't have access to
        permissions = target_message.channel.permissions_for(ctx.author)
        if not permissions.read_messages:
            embed = discord.Embed(
                title="Permission",
                color=ctx.author.color,
                description="You don't have permission to view this channel.",
            )
            await ctx.send(embed=embed)
            return

        def event_check(reaction: discord.Reaction, user: discord.Member) -> bool:
            """Make sure that this reaction is what we want to operate on."""
            return (
                # Conditions for a successful pagination:
                all(
                    (
                        # Reaction is on this message
                        reaction.message.id == reaction_message.id,
                        # User has not already bookmarked this message
                        user.id not in bookmarked_users,
                        # Reaction is the `BOOKMARK_EMOJI` emoji
                        str(reaction.emoji) == BOOKMARK_EMOJI,
                        # Reaction was not made by the Bot
                        user.id != self.bot.user.id,
                    )
                )
            )

        await self.action_bookmark(ctx.channel, ctx.author, target_message, title)

        # Keep track of who has already bookmarked, so users can't spam reactions and cause loads of DMs
        bookmarked_users = [ctx.author.id]
        reaction_message = await self.send_reaction_embed(ctx.channel, target_message)

        try:
            _, user = await self.bot.wait_for(
                "reaction_add", timeout=TIMEOUT, check=event_check
            )
        except asyncio.TimeoutError:
            return await reaction_message.delete(delay=0)

        await self.action_bookmark(ctx.channel, user, target_message, title)
        bookmarked_users.append(user.id)

    async def kata_id(self, search_link: str, params: dict) -> Union[str, Embed]:
        """
        Uses bs4 to get the HTML code for the page of katas, where the page is the link of the formatted `search_link`.
        This will webscrape the search page with `search_link` and then get the ID of a kata for the
        codewars.com API to use.
        """
        async with self.bot.http_session.get(search_link, params=params) as response:
            if response.status != 200:
                error_embed = Embed(
                    title=choice(NEGATIVE_REPLIES),
                    description="We ran into an error when getting the kata from codewars.com, try again later.",
                    color=0xCD6D6D,
                )
                return error_embed

            soup = BeautifulSoup(
                await response.text(), features="html.parser"
            )  # changed the parser
            first_kata_div = await asyncio.to_thread(
                soup.find_all, "div", class_="item-title px-0"
            )

            if not first_kata_div:
                raise commands.BadArgument(
                    "No katas could be found with the filters provided."
                )
            if len(first_kata_div) >= 3:
                first_kata_div = choice(first_kata_div[:3])
            elif "q=" not in search_link:
                first_kata_div = choice(first_kata_div)
            else:
                first_kata_div = first_kata_div[0]

            # There are numerous divs before arriving at the id of the kata, which can be used for the link.
            first_kata_id = first_kata_div.a["href"].split("/")[-1]
            return first_kata_id

    async def kata_information(self, kata_id: str) -> Union[dict, Embed]:
        """
        Returns the information about the Kata.
        Uses the codewars.com API to get information about the kata using `kata_id`.
        """
        async with self.bot.http_session.get(
            API_ROOT.format(kata_id=kata_id)
        ) as response:
            if response.status != 200:
                error_embed = Embed(
                    title=choice(NEGATIVE_REPLIES),
                    description="We ran into an error when getting the kata information, try again later.",
                    color=0xCD6D6D,
                )
                return error_embed

            return await response.json()

    @staticmethod
    def main_embed(kata_information: dict) -> Embed:
        """Creates the main embed which displays the name, difficulty and description of the kata."""
        kata_description = kata_information["description"]
        kata_url = f"https://codewars.com/kata/{kata_information['id']}"

        # Ensuring it isn't over the length 1024
        if len(kata_description) > 1024:
            kata_description = (
                "\n".join(kata_description[:1000].split("\n")[:-1]) + "..."
            )
            kata_description += f" [continue reading]({kata_url})"

        if kata_information["rank"]["name"] is None:
            embed_color = 8
            kata_difficulty = "Unable to retrieve difficulty for beta languages."
        else:
            embed_color = int(kata_information["rank"]["name"].replace(" kyu", ""))
            kata_difficulty = kata_information["rank"]["name"]

        kata_embed = Embed(
            title=kata_information["name"],
            description=kata_description,
            color=MAPPING_OF_KYU[embed_color],
            url=kata_url,
        )
        kata_embed.add_field(name="Difficulty", value=kata_difficulty, inline=False)
        return kata_embed

    @staticmethod
    def language_embed(kata_information: dict) -> Embed:
        """Creates the 'language embed' which displays all languages the kata supports."""
        kata_url = f"https://codewars.com/kata/{kata_information['id']}"

        languages = "\n".join(map(str.title, kata_information["languages"]))
        language_embed = Embed(
            title=kata_information["name"],
            description=f"```yaml\nSupported Languages:\n{languages}\n```",
            url=kata_url,
        )
        return language_embed

    @staticmethod
    def tags_embed(kata_information: dict) -> Embed:
        """
        Creates the 'tags embed' which displays all the tags of the Kata.
        Tags explain what the kata is about, this is what codewars.com calls categories.
        """
        kata_url = f"https://codewars.com/kata/{kata_information['id']}"

        tags = "\n".join(kata_information["tags"])
        tags_embed = Embed(
            title=kata_information["name"],
            description=f"```yaml\nTags:\n{tags}\n```",
            color=0xCD6D6D,
            url=kata_url,
        )
        return tags_embed

    @staticmethod
    def miscellaneous_embed(kata_information: dict) -> Embed:
        """
        Creates the 'other information embed' which displays miscellaneous information about the kata.
        This embed shows statistics such as the total number of people who completed the kata,
        the total number of stars of the kata, etc.
        """
        kata_url = f"https://codewars.com/kata/{kata_information['id']}"

        embed = Embed(
            title=kata_information["name"],
            description="```nim\nOther Information\n```",
            color=0xCD6D6D,
            url=kata_url,
        )
        embed.add_field(
            name="`Total Score`",
            value=f"```css\n{kata_information['voteScore']}\n```",
            inline=False,
        )
        embed.add_field(
            name="`Total Stars`",
            value=f"```css\n{kata_information['totalStars']}\n```",
            inline=False,
        )
        embed.add_field(
            name="`Total Completed`",
            value=f"```css\n{kata_information['totalCompleted']}\n```",
            inline=False,
        )
        embed.add_field(
            name="`Total Attempts`",
            value=f"```css\n{kata_information['totalAttempts']}\n```",
            inline=False,
        )
        return embed

    @staticmethod
    def create_view(dropdown: InformationDropdown, link: str) -> ui.View:
        """
        Creates the discord.py View for the Discord message components (dropdowns and buttons).
        The discord UI is implemented onto the embed, where the user can choose what information about the kata they
        want, along with a link button to the kata itself.
        """
        view = ui.View()
        view.add_item(dropdown)
        view.add_item(ui.Button(label="View the Kata", url=link))
        return view

    @commands.command(aliases=["kata"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def challenge(
        self, ctx: Context, language: str = "python", *, query: str = None
    ) -> None:
        """
        The challenge command pulls a random kata (challenge) from codewars.com.
        The different ways to use this command are:
        `.challenge <language>` - Pulls a random challenge within that language's scope.
        `.challenge <language> <difficulty>` - The difficulty can be from 1-8,
        1 being the hardest, 8 being the easiest. This pulls a random challenge within that difficulty & language.
        `.challenge <language> <query>` - Pulls a random challenge with the query provided under the language
        `.challenge <language> <query>, <difficulty>` - Pulls a random challenge with the query provided,
        under that difficulty within the language's scope.
        """
        language = language.lower()
        if language not in SUPPORTED_LANGUAGES["stable"] + SUPPORTED_LANGUAGES["beta"]:
            raise commands.BadArgument(
                "This is not a recognized language on codewars.com!"
            )

        get_kata_link = f"https://codewars.com/kata/search/{language}"
        params = {}

        if query is not None:
            if "," in query:
                query_splitted = query.split("," if ", " not in query else ", ")

                if len(query_splitted) > 2:
                    raise commands.BadArgument(
                        "There can only be one comma within the query, separating the difficulty and the query itself."
                    )

                query, level = query_splitted
                params["q"] = query
                params["r[]"] = f"-{level}"
            elif query.isnumeric():
                params["r[]"] = f"-{query}"
            else:
                params["q"] = query

        params["beta"] = str(language in SUPPORTED_LANGUAGES["beta"]).lower()

        first_kata_id = await self.kata_id(get_kata_link, params)
        if isinstance(first_kata_id, Embed):
            # We ran into an error when retrieving the website link
            await ctx.send(embed=first_kata_id)
            return

        kata_information = await self.kata_information(first_kata_id)
        if isinstance(kata_information, Embed):
            # Something went wrong when trying to fetch the kata information
            await ctx.d(embed=kata_information)
            return

        kata_embed = self.main_embed(kata_information)
        language_embed = self.language_embed(kata_information)
        tags_embed = self.tags_embed(kata_information)
        miscellaneous_embed = self.miscellaneous_embed(kata_information)

        dropdown = InformationDropdown(
            main_embed=kata_embed,
            language_embed=language_embed,
            tags_embed=tags_embed,
            other_info_embed=miscellaneous_embed,
        )
        kata_view = self.create_view(
            dropdown, f"https://codewars.com/kata/{first_kata_id}"
        )
        original_message = await ctx.send(embed=kata_embed, view=kata_view)
        dropdown.original_message = original_message

        wait_for_kata = await kata_view.wait()
        if wait_for_kata:
            await original_message.edit(embed=kata_embed, view=None)
