from __future__ import annotations

import asyncio
import hashlib
import os
import re
import sys
import unicodedata
import urllib.parse
from collections.abc import Callable
from html import unescape
from io import BytesIO
from random import choice, random
from typing import Any
from urllib.parse import quote, quote_plus

import aiohttp
import arrow
import rapidfuzz
from aiofile import async_open
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from jishaku.paginators import PaginatorEmbedInterface
from rapidfuzz.process import extractOne

import discord
from core import Cog, Context, Parrot
from discord import app_commands
from discord.ext import commands, tasks
from utilities import hastebin
from utilities.converters import WrappedMessageConverter

from . import _doc, _ref
from ._used import execute_run, get_raw, prepare_payload
from ._utils import (
    ANSI_RE,
    API_ROOT,
    API_ROOT_RP,
    ARTICLE_URL,
    BASE_URL,
    BASE_URL_SO,
    BOOKMARK_EMOJI,
    ERROR_MESSAGE,
    ERROR_MESSAGE_CHEAT_SHEET,
    ESCAPE_TT,
    GITHUB_API_URL,
    HEADERS,
    MAPPING_OF_KYU,
    MINIMUM_CERTAINTY,
    NEGATIVE_REPLIES,
    SEARCH_URL_REAL,
    SEARCH_URL_SO,
    SO_PARAMS,
    SUPPORTED_LANGUAGES,
    TIMEOUT,
    URL,
    WTF_PYTHON_RAW_URL,
    Icons,
    InformationDropdown,
)
from ._kontests import CodeChef, CodeForces, AtCoder, HackerRank, HackerEarth, CSAcademy
try:
    import lxml  # noqa: F401  # pylint: disable=unused-import

    HTML_PARSER = "lxml"
except ImportError:
    HTML_PARSER = "html.parser"

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class BookmarkForm(discord.ui.Modal):
    """The form where a user can fill in a custom title for their bookmark & submit it."""

    bookmark_title = discord.ui.TextInput(
        label="Choose a title for your bookmark (optional)",
        placeholder="Type your bookmark title here",
        default="Bookmark",
        max_length=50,
        min_length=0,
        required=False,
    )

    def __init__(self, message: discord.Message) -> None:
        super().__init__(timeout=1000, title="Name your bookmark")
        self.message = message

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Sends the bookmark embed to the user with the newly chosen title."""
        title = self.bookmark_title.value or self.bookmark_title.default
        try:
            await self.dm_bookmark(interaction, self.message, title)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=RTFM.build_error_embed("Enable your DMs to receive the bookmark."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=RTFM.build_success_reply_embed(self.message),
            ephemeral=True,
        )

    async def dm_bookmark(
        self,
        interaction: discord.Interaction,
        target_message: discord.Message,
        title: str | None,
    ) -> None:
        """Sends the target_message as a bookmark to the interaction user's DMs.

        Raises ``discord.Forbidden`` if the user's DMs are closed.
        """
        embed = RTFM.build_bookmark_dm(target_message, title)
        message_url_view = discord.ui.View().add_item(discord.ui.Button(label="View Message", url=target_message.jump_url))
        await interaction.user.send(embed=embed, view=message_url_view)


class RTFM(Cog):
    """To test code and check docs. Thanks to https://github.com/FrenchMasterSword/RTFMbot."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.algos = sorted([h for h in hashlib.algorithms_available if h.islower()])
        self.ON_TESTING = False
        self.headers: dict[str, str] = {}
        self.fetch_readme.start()
        self.__bookmark_context_menu_callback = app_commands.ContextMenu(
            name="Bookmark",
            callback=self._bookmark_context_menu_callback,
        )
        self.bot.tree.add_command(self.__bookmark_context_menu_callback)
        self._python_cached: dict[str, str] = {}
        self._roadmap_cached: dict[str, str] = {}
        self.hastebin = hastebin.HTTPClient(session=self.bot.http_session)

    @tasks.loop(minutes=60)
    async def fetch_readme(self) -> None:
        """Gets the content of README.md from the WTF Python Repository."""
        async with self.bot.http_session.get(f"{WTF_PYTHON_RAW_URL}README.md") as resp:
            if resp.status == 200:
                raw = await resp.text()
                self.parse_readme(raw)

    @staticmethod
    def build_bookmark_dm(target_message: discord.Message, title: str | None) -> discord.Embed:
        """Build the embed to DM the bookmark requester."""
        embed = discord.Embed(
            title=title or "Bookmark",
            description=target_message.content,
        )
        if target_message.attachments and target_message.attachments[0].url.endswith(("png", "jpeg", "jpg", "gif", "webp")):
            embed.set_image(url=target_message.attachments[0].url)

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
    def build_success_reply_embed(target_message: discord.Message) -> discord.Embed:
        """Build the ephemeral reply embed to the bookmark requester."""
        return discord.Embed(
            description=(f"A bookmark for [this message]({target_message.jump_url}) has been successfully sent your way."),
            color=discord.Color.green(),
        )

    async def _bookmark_context_menu_callback(self, interaction: discord.Interaction, message: discord.Message) -> None:
        """The callback that will be invoked upon using the bookmark's context menu command."""
        assert isinstance(interaction.user, discord.Member) and isinstance(interaction.channel, discord.abc.GuildChannel)
        permissions = interaction.channel.permissions_for(interaction.user)
        if not permissions.read_messages:
            embed = self.build_error_embed("You don't have permission to view this channel.")
            await interaction.response.send_message(embed=embed)
            return

        bookmark_title_form = BookmarkForm(message=message)
        await interaction.response.send_modal(bookmark_title_form)

    @staticmethod
    def build_error_embed(user: discord.Member | discord.User | str) -> discord.Embed:
        """Builds an error embed for when a bookmark requester has DMs disabled."""
        if isinstance(user, str):
            return discord.Embed(
                title="You DM(s) are closed!",
                description=user,
            )

        return discord.Embed(
            title="You DM(s) are closed!",
            description=f"{user.mention}, please enable your DMs to receive the bookmark.",
        )

    async def action_bookmark(
        self,
        channel: discord.abc.MessageableChannel,
        user: discord.Member | discord.User,
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
        channel: discord.abc.MessageableChannel,
        target_message: discord.Message,
    ) -> discord.Message:
        """Sends an embed, with a reaction, so users can react to bookmark the message too."""
        message = await channel.send(
            embed=discord.Embed(
                description=(
                    f"React with {BOOKMARK_EMOJI} to be sent your very own bookmark to "
                    f"[this message]({target_message.jump_url})."
                ),
            ),
        )

        await message.add_reaction(BOOKMARK_EMOJI)
        return message

    def parse_readme(self, data: str) -> None:
        # Match the start of examples, until the end of the table of contents (toc)
        table_of_contents = re.search(r"\[👀 Examples\]\(#-examples\)\n([\w\W]*)<!-- tocstop -->", data)[0].split("\n")

        for header in list(map(str.strip, table_of_contents)):
            if match := re.search(r"\[▶ (.*)\]\((.*)\)", header):
                hyper_link = match[0].split("(")[1].replace(")", "")
                self.headers[match[0]] = f"{BASE_URL}/{hyper_link}"

    def fuzzy_match_header(self, query: str) -> str | None:
        match, certainty, _ = rapidfuzz.process.extractOne(query, self.headers.keys())
        return match if certainty > MINIMUM_CERTAINTY else None

    def get_content(self, tag: BeautifulSoup):
        """Returns content between two h2 tags."""
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
            content = f"{content[:1021]}..."

        return re.sub(r" +", " ", content)

    referred: dict[str, Callable] = {
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
    documented: dict[str, Callable] = {
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
        return self.bot.http_session

    @staticmethod
    def fmt_error_embed() -> discord.Embed:
        """Format the Error Embed.
        If the cht.sh search returned 404, overwrite it to send a custom error embed.
        link -> https://github.com/chubin/cheat.sh/issues/198.
        """
        return discord.Embed(
            title="! You done? !",
            description=ERROR_MESSAGE_CHEAT_SHEET,
        )

    async def get_package(self, url: str):
        return await self.session.get(url=url)

    async def build_python_cache(self):
        if not hasattr(self, "_python_cached"):
            self._python_cached = {}

        for file in os.listdir("extra/tutorials/python"):
            if file.endswith(".md"):
                async with async_open(f"extra/tutorials/python/{file}") as f:
                    self._python_cached[file.replace(".md", "")] = await f.read()

    @commands.group(invoke_without_command=True)
    @Context.with_type
    async def python(self, ctx: Context, *, text: str):
        """Search for a python tutorial."""
        if ctx.invoked_subcommand is not None:
            return
        if not getattr(self, "_python_cached", None):
            await self.build_python_cache()

        # get closest match
        match = await asyncio.to_thread(extractOne, text, self._python_cached.keys())
        if match[1] < 50:
            return await ctx.send(
                embed=discord.Embed(
                    description="No such tutorial found in the search query.",
                    color=self.bot.color,
                ),
            )
        if 70 < match[1] < 90:
            val = await ctx.prompt(f"{ctx.author.mention} Did you mean `{match[0]}`?")
            if val:
                data = self._python_cached[match[0]]
            else:
                await ctx.send(
                    f"{ctx.author.mention} No tag found with your query, you can ask the developer to create one.\n"
                    f"Or consider contributing to the project by creating a tag yourself.\n"
                    f"See <{self.bot.github}> | `{ctx.prefix}python list` for a list of available tags.",
                )
                return
        else:
            data = self._python_cached[match[0]]
        await ctx.send(embed=discord.Embed(description=data))

    @python.command(name="list")
    @Context.with_type
    async def python_list(self, ctx: Context):
        if not getattr(self, "_python_cached", None):
            await self.build_python_cache()

        await ctx.send(
            embed=discord.Embed(
                title="List of available tutorials",
                description="`" + "`, `".join(self._python_cached.keys()) + "`",
                color=self.bot.color,
            ),
        )

    @commands.command(aliases=["pypi"])
    @Context.with_type
    async def pypisearch(self, ctx: Context, arg: str):
        """Get info about a Python package directly from PyPi."""
        res_raw = await self.get_package(f"https://pypi.org/pypi/{arg}/json")

        try:
            res_json = await res_raw.json()
        except aiohttp.ContentTypeError:
            return await ctx.send(
                embed=discord.Embed(
                    description="No such package found in the search query.",
                    color=self.bot.color,
                ),
            )

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
            discord.Embed(
                title=f"{name} PyPi Stats",
                description=description,
                color=discord.Color.teal(),
            )
            .add_field(name="Author", value=author, inline=True)
            .add_field(name="Author Email", value=author_email, inline=True)
            .add_field(name="Version", value=version, inline=False)
            .add_field(name="License", value=_license, inline=True)
            .add_field(name="Project Url", value=project_url, inline=False)
            .add_field(name="Home Page", value=home_page)
            .set_thumbnail(url="https://i.imgur.com/syDydkb.png")
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=["npm"])
    @Context.with_type
    async def npmsearch(self, ctx: Context, arg: str):
        """Get info about a NPM package directly from the NPM Registry."""
        res_raw = await self.get_package(f"https://registry.npmjs.org/{arg}/")

        res_json = await res_raw.json()

        if res_json.get("error"):
            return await ctx.send(
                embed=discord.Embed(
                    description="No such package found in the search query.",
                    color=0xCC3534,
                ),
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
            .set_thumbnail(
                url="https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Npm-logo.svg/800px-Npm-logo.svg.png",
            )
        )

        await ctx.send(embed=em)

    @commands.command(aliases=["crates"])
    @Context.with_type
    async def crate(self, ctx: Context, arg: str):
        """Get info about a Rust package directly from the Crates.IO Registry."""
        res_raw = await self.get_package(f"https://crates.io/api/v1/crates/{arg}")

        res_json = await res_raw.json()

        if res_json.get("errors"):
            return await ctx.send(
                embed=discord.Embed(
                    description="No such package found in the search query.",
                    color=0xE03D29,
                ),
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

        em = (
            discord.Embed(
                title=f"{pkg_name} crates.io Stats",
                description=description,
                color=0xE03D29,
            )
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

        await ctx.send(embed=em)

    @commands.group(
        usage="<language> [--wrapped] [--stats] <code>",
        brief="Execute code in a given programming language",
        invoke_without_command=True,
    )
    async def run(self, ctx: Context, *, payload: str = ""):
        """For command-line-options, compiler-flags and arguments you may add a line starting with this argument,
        and after a space add your options, flags or args.

        Stats option displays more informations on execution consumption
        wrapped allows you to not put main function in some languages,
        which you can see in `list wrapped argument` <code> may be normal code,
        but also an attached file, or a link from [hastebin](https://hastebin.com) or [Github gist](https://gist.github.com)

        If you use a link, your command must end with this syntax:
            `link=<link>` (no space around `=`)

        For instance: `$run python link=https://hastebin.com/resopedahe.py`

        The link may be the raw version, and with/without the file extension

        If the output exceeds 40 lines or Discord max message length, it will be put
        in a new hastebin and the link will be returned.
        """
        if not payload:
            emb = discord.Embed(
                title="SyntaxError",
                description="Command `run` missing a required argument: `language`",
                colour=0xFF0000,
            )
            return await ctx.send(embed=emb)

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
            base_url = urllib.parse.quote_plus(payload.split(" ")[-1][5:].strip("/"), safe=";/?:@&=$,><-[]")

            url = get_raw(base_url)

            async with self.bot.http_session.get(url) as response:
                if response.status == 404:
                    return await ctx.send("Nothing found. Check your link")
                if response.status != 200:
                    return await ctx.send(f"An error occurred (status code: {response.status}). Retry later.")
                text = await response.text()
                if len(text) > 20000:
                    return await ctx.send("Code must be shorter than 20,000 characters.")
                lang = re.split(r"\s+", payload, maxsplit=1)[0]
        else:
            language, text, errored = prepare_payload(
                payload,
            )  # we call it text but it's an embed if it errored #JustDynamicTypingThings

            if errored:
                return await ctx.send(embed=text)

        async with ctx.typing():
            if lang:
                language = lang

            assert isinstance(text, str)
            output = await execute_run(self.bot, language, text)

            await ctx.reply(output)

    @commands.command(aliases=["ref"])
    @Context.with_type
    async def reference(self, ctx: Context, language: str, *, query: str):
        """Returns element reference from given language."""
        lang = language.strip("`")

        if lang.lower() not in self.referred:
            return await ctx.reply(f"{lang} not available. See `[p]list references` for available ones.")
        await self.referred[lang.lower()](ctx, query.strip("`"))

    @commands.command(aliases=["doc"])
    @Context.with_type
    async def documentation(self, ctx: Context, language: str, *, query: str):
        """Returns element reference from given language."""
        lang = language.strip("`")

        if lang.lower() not in self.documented:
            return await ctx.reply(f"{lang} not available. See `{ctx.prefix}list documentations` for available ones.")
        await self.documented[lang.lower()](ctx, query.strip("`"))

    @commands.command()
    @Context.with_type
    async def man(self, ctx: Context, *, page: str):
        """Returns the manual's page for a (mostly Debian) linux command."""
        base_url = f"https://man.cx/{page}"
        url = urllib.parse.quote_plus(base_url, safe=";/?:@&=$,><-[]")

        async with aiohttp.ClientSession() as client_session:
            async with client_session.get(url) as response:
                if response.status != 200:
                    return await ctx.reply("An error occurred (status code: {response.status}). Retry later.")

                soup = BeautifulSoup(await response.text(), HTML_PARSER)

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

                emb = (
                    discord.Embed(title=title, url=f"https://man.cx/{page}")
                    .set_author(name="Debian Linux man pages")
                    .set_thumbnail(url="https://www.debian.org/logos/openlogo-nd-100.png")
                )

                for tag in contents:
                    h2 = tuple(soup.find(attrs={"name": tuple(tag.children)[0].get("href")[1:]}).parents)[0]
                    emb.add_field(name=tag.string, value=self.get_content(h2), inline=False)

                await ctx.reply(embed=emb)

    @commands.command()
    async def ascii(self, ctx: Context, *, text: str):
        """Returns number representation of characters in text."""
        emb = discord.Embed(
            title="Unicode convert",
            description=" ".join([str(ord(letter)) for letter in text]),
        ).set_footer(text=f"Invoked by {str(ctx.message.author)}")
        await ctx.reply(embed=emb)

    @commands.command()
    async def unascii(self, ctx: Context, *, text: str):
        """Reforms string from char codes."""
        try:
            codes = [chr(int(i)) for i in text.split(" ")]

            await ctx.reply(
                embed=discord.Embed(title="Unicode convert", description="".join(codes)).set_footer(
                    text=f"Invoked by {str(ctx.message.author)}",
                ),
            )
        except ValueError:
            await ctx.reply("Invalid sequence. Example usage : `[p]unascii 104 101 121`")

    @commands.command()
    async def byteconvert(self, ctx: Context, value: int, unit=None):
        """Shows byte conversions of given value."""
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
    async def _hash(self, ctx: Context, algorithm: str, *, text: str):
        """Hashes text with a given algorithm
        UTF-8, returns under hexadecimal form.
        """
        algo = algorithm.lower()

        if algo not in self.algos:
            message = f"`{algorithm}` not available."
            if matches := "\n".join([supported for supported in self.algos if algo in supported][:10]):
                message += f" Did you mean:\n{matches}"
            return await ctx.reply(message)

        try:
            # Guaranteed one
            hash_object = getattr(hashlib, algo)(text.encode("utf-8"))
        except AttributeError:
            # Available
            hash_object = hashlib.new(algo, text.encode("utf-8"))

        emb = discord.Embed(title=f"{algorithm} hash", description=hash_object.hexdigest()).set_footer(
            text=f"Invoked by {str(ctx.message.author)}",
        )

        await ctx.reply(embed=emb)

    @commands.command()
    async def charinfo(self, ctx, *, characters: str):
        """Shows you information about a number of characters.
        Only up to 25 characters at a time.
        """

        def to_string(c):
            digit = f"{ord(c):x}"
            name = unicodedata.name(c, "Name not found.")
            return f"`\\U{digit:>08}`: {name} - {c} \N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>"

        msg = "\n".join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.send("Output too long to display.")
        await ctx.send(msg)

    async def fetch_data(self, url: str) -> dict[str, Any]:
        """Retrieve data as a dictionary."""
        async with self.bot.http_session.get(url) as r:
            return await r.json()

    @commands.group(name="github", aliases=("gh", "git", "g"))  # Thanks `will.#0021` (211756205721255947)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def github_group(self, ctx: Context) -> None:
        """Commands for finding information related to GitHub."""
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)

    @github_group.command(name="user", aliases=("userinfo", "u"))  # Thanks `will.#0021` (211756205721255947)
    async def github_user_info(self, ctx: Context, username: str) -> None:
        """Fetches a user's GitHub information."""
        async with ctx.typing():
            user_data = await self.fetch_data(f"{GITHUB_API_URL}/users/{quote_plus(username)}")

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
            orgs = [f"[{org['login']}](https://github.com/{org['login']})" for org in org_data]
            orgs_to_add = " | ".join(orgs)

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
                    description=f"```\n{user_data['bio']}\n```\n" if user_data["bio"] else "",
                    colour=discord.Colour.og_blurple(),
                    url=user_data["html_url"],
                    timestamp=arrow.get(user_data["created_at"]).datetime,
                )
                .set_thumbnail(url=user_data["avatar_url"])
                .set_footer(text="Account created at")
                .add_field(
                    name="Public repos",
                    value=f"[{user_data['public_repos']}]({user_data['html_url']}?tab=repositories)",
                )
                .add_field(name="Website", value=blog)
            )

            if user_data["type"] == "User":
                embed.add_field(
                    name="Followers",
                    value=f"[{user_data['followers']}]({user_data['html_url']}?tab=followers)",
                ).add_field(
                    name="Following",
                    value=f"[{user_data['following']}]({user_data['html_url']}?tab=following)",
                )

            if user_data["type"] == "User":
                embed.add_field(
                    name="Gists",
                    value=f"[{gists}](https://gist.github.com/{quote_plus(username, safe='')})",
                ).add_field(
                    name=f"Organization{'s' if len(orgs)!=1 else ''}",
                    value=orgs_to_add if orgs else "No organizations.",
                )

        await ctx.send(embed=embed)

    @github_group.command(name="repository", aliases=("repo", "r"))  # Thanks ``willdn`` (will.#0021 - 211756205721255947)
    async def github_repo_info(self, ctx: Context, *repo: str) -> None:
        """Fetches a repositories' GitHub information.
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
            embed.description += f"\n\nForked from [{parent['full_name']}]({parent['html_url']})"
        except KeyError:
            pass

        repo_owner = repo_data["owner"]

        embed.set_author(
            name=repo_owner["login"],
            url=repo_owner["html_url"],
            icon_url=repo_owner["avatar_url"],
        )

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

        await ctx.send(embed=embed)

    @commands.command(aliases=["rp"])
    @commands.cooldown(1, 10, commands.cooldowns.BucketType.user)
    async def realpython(
        self,
        ctx: Context,
        amount: int | None = 5,
        *,
        user_search: str | None = None,
    ) -> None:
        """Send some articles from RealPython that match the search terms.
        By default the top 5 matches are sent, this can be overwritten to a number between 1 and 5 by specifying an amount before the search query.
        If no search query is specified by the user, the home page is sent.
        """
        if user_search is None:
            home_page_embed = discord.Embed(
                title="Real Python Home Page",
                url="https://realpython.com/",
                colour=ctx.author.color,
            )
            await ctx.send(embed=home_page_embed)
            return

        if not 1 <= (amount or 5) <= 5:
            await ctx.send(f"{ctx.author.mention} `amount` must be between 1 and 5 (inclusive).")
            return

        params = {"q": user_search, "limit": amount, "kind": "article"}
        async with self.bot.http_session.get(url=API_ROOT_RP, params=params) as response:
            if response.status != 200:
                await ctx.send(
                    embed=discord.Embed(
                        title="Error while searching Real Python",
                        description="There was an error while trying to reach Real Python. Please try again shortly.",
                        color=ctx.author.color,
                    ),
                )
                return

            data = await response.json()

        articles = data["results"]

        if len(articles) == 0:
            no_articles = discord.Embed(title=f"No articles found for '{user_search}'", color=ctx.author.color)
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
    async def stackoverflow(self, ctx: Context, *, search_query: str) -> None:
        """Sends the top 5 results of a search query from stackoverflow."""
        params = {**SO_PARAMS, "q": search_query}
        async with self.bot.http_session.get(url=BASE_URL_SO, params=params) as response:
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
                    ),
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
    @Context.with_type
    async def cheat_sheet(self, ctx: Context, *search_terms: str) -> None:
        """Search cheat.sh.
        Gets a post from https://cheat.sh/python/ by default.
        Usage:
        --> $cht read json.
        """
        search_string = quote_plus(" ".join(search_terms))

        async with self.bot.http_session.get(
            URL.format(
                search=search_string,
            ),
            headers=HEADERS,
        ) as response:
            result = ANSI_RE.sub("", await response.text()).translate(ESCAPE_TT)

        page = commands.Paginator(prefix="```python", suffix="```", max_size=1980)
        for line in result.splitlines():
            page.add_line(line)

        interface = PaginatorEmbedInterface(ctx.bot, page, owner=ctx.author)
        await interface.send_to(ctx)

    @commands.command(aliases=["wtfp"])
    async def wtfpython(self, ctx: Context, *, query: str | None = None) -> None:
        """Search WTF Python repository.
        Gets the link of the fuzzy matched query from https://github.com/satwikkansal/wtfpython.
        Usage:
            --> $wtfp wild imports.
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
            embed = discord.Embed(title="! Well !", description=ERROR_MESSAGE, colour=ctx.author.color)
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

    async def cog_unload(self) -> None:
        """Unload the cog and cancel the task."""
        self.fetch_readme.cancel()

    @commands.command(name="bookmark", aliases=("bm", "pin"))
    async def bookmark(
        self,
        ctx: Context,
        target_message: WrappedMessageConverter | None,
        *,
        title: str = "Bookmark",
    ) -> None:
        """Send the author a link to `target_message` via DMs."""
        if not target_message:
            if not ctx.message.reference:
                msg = "You must either provide a valid message to bookmark, or reply to one.\n\nThe lookup strategy for a message is as follows (in order):\n1. Lookup by '{channel ID}-{message ID}' (retrieved by shift-clicking on 'Copy ID')\n2. Lookup by message ID (the message **must** be in the context channel)\n3. Lookup by message URL"
                raise commands.BadArgument(
                    msg,
                )
            target_message = ctx.message.reference.resolved

        if not target_message:
            msg = "Couldn't find that message."
            raise commands.BadArgument(msg)

        assert isinstance(target_message, discord.Message) and isinstance(ctx.author, discord.Member)

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
                    ),
                )
            )

        assert isinstance(target_message, discord.Message)

        await self.action_bookmark(ctx.channel, ctx.author, target_message, title)

        # Keep track of who has already bookmarked, so users can't spam reactions and cause loads of DMs
        bookmarked_users = [ctx.author.id]
        reaction_message = await self.send_reaction_embed(ctx.channel, target_message)

        try:
            _, user = await self.bot.wait_for("reaction_add", timeout=TIMEOUT, check=event_check)
        except asyncio.TimeoutError:
            return await reaction_message.delete(delay=0)

        await self.action_bookmark(ctx.channel, user, target_message, title)
        bookmarked_users.append(user.id)

    async def kata_id(self, search_link: str, params: dict[str, Any]) -> str | discord.Embed:
        """Uses bs4 to get the HTML code for the page of katas, where the page is the link of the formatted `search_link`.
        This will webscrape the search page with `search_link` and then get the ID of a kata for the
        codewars.com API to use.
        """
        async with self.bot.http_session.get(search_link, params=params) as response:
            if response.status != 200:
                return discord.Embed(
                    title=choice(NEGATIVE_REPLIES),
                    description="We ran into an error when getting the kata from codewars.com, try again later.",
                    color=0xCD6D6D,
                )

            soup = BeautifulSoup(await response.text(), features=HTML_PARSER)  # changed the parser
            first_kata_div = _doc.get_ele(soup, "div", class_="item-title px-0")

            if not first_kata_div:
                msg = "No katas could be found with the filters provided."
                raise commands.BadArgument(msg)
            if len(first_kata_div) >= 3:
                first_kata_div = choice(first_kata_div[:3])
            elif "q=" not in search_link:
                first_kata_div = choice(first_kata_div)
            else:
                first_kata_div = first_kata_div[0]

            return first_kata_div.a["href"].split("/")[-1]

    async def kata_information(self, kata_id: str) -> dict[str, Any] | discord.Embed:
        """Returns the information about the Kata.
        Uses the codewars.com API to get information about the kata using `kata_id`.
        """
        async with self.bot.http_session.get(API_ROOT.format(kata_id=kata_id)) as response:
            if response.status != 200:
                return discord.Embed(
                    title=choice(NEGATIVE_REPLIES),
                    description="We ran into an error when getting the kata information, try again later.",
                    color=0xCD6D6D,
                )

            return await response.json()

    @staticmethod
    def main_embed(kata_information: dict[str, Any]) -> discord.Embed:
        """Creates the main embed which displays the name, difficulty and description of the kata."""
        kata_description = kata_information["description"]
        kata_url = f"https://codewars.com/kata/{kata_information['id']}"

        # Ensuring it isn't over the length 1024
        if len(kata_description) > 1024:
            kata_description = "\n".join(kata_description[:1000].split("\n")[:-1]) + "..."
            kata_description += f" [continue reading]({kata_url})"

        if kata_information["rank"]["name"] is None:
            embed_color = 8
            kata_difficulty = "Unable to retrieve difficulty for beta languages."
        else:
            embed_color = int(kata_information["rank"]["name"].replace(" kyu", ""))
            kata_difficulty = kata_information["rank"]["name"]

        kata_embed = discord.Embed(
            title=kata_information["name"],
            description=kata_description,
            color=MAPPING_OF_KYU[embed_color],
            url=kata_url,
        )
        kata_embed.add_field(name="Difficulty", value=kata_difficulty, inline=False)
        return kata_embed

    @staticmethod
    def language_embed(kata_information: dict[str, Any]) -> discord.Embed:
        """Creates the 'language embed' which displays all languages the kata supports."""
        kata_url = f"https://codewars.com/kata/{kata_information['id']}"

        languages = "\n".join(map(str.title, kata_information["languages"]))
        return discord.Embed(
            title=kata_information["name"],
            description=f"```yaml\nSupported Languages:\n{languages}\n```",
            url=kata_url,
        )

    @staticmethod
    def tags_embed(kata_information: dict[str, Any]) -> discord.Embed:
        """Creates the 'tags embed' which displays all the tags of the Kata.
        Tags explain what the kata is about, this is what codewars.com calls categories.
        """
        kata_url = f"https://codewars.com/kata/{kata_information['id']}"

        tags = "\n".join(kata_information["tags"])
        return discord.Embed(
            title=kata_information["name"],
            description=f"```yaml\nTags:\n{tags}\n```",
            color=0xCD6D6D,
            url=kata_url,
        )

    @staticmethod
    def miscellaneous_embed(kata_information: dict) -> discord.Embed:
        """Creates the 'other information embed' which displays miscellaneous information about the kata.
        This embed shows statistics such as the total number of people who completed the kata,
        the total number of stars of the kata, etc.
        """
        kata_url = f"https://codewars.com/kata/{kata_information['id']}"

        return (
            discord.Embed(
                title=kata_information["name"],
                description="```nim\nOther Information\n```",
                color=0xCD6D6D,
                url=kata_url,
            )
            .add_field(
                name="`Total Score`",
                value=f"```css\n{kata_information['voteScore']}\n```",
                inline=False,
            )
            .add_field(
                name="`Total Stars`",
                value=f"```css\n{kata_information['totalStars']}\n```",
                inline=False,
            )
            .add_field(
                name="`Total Completed`",
                value=f"```css\n{kata_information['totalCompleted']}\n```",
                inline=False,
            )
            .add_field(
                name="`Total Attempts`",
                value=f"```css\n{kata_information['totalAttempts']}\n```",
                inline=False,
            )
        )

    @staticmethod
    def create_view(dropdown: InformationDropdown, link: str) -> discord.ui.View:
        """Creates the discord.py View for the Discord message components (dropdowns and buttons).
        The discord UI is implemented onto the embed, where the user can choose what information about the kata they
        want, along with a link button to the kata itself.
        """
        view = discord.ui.View()
        view.add_item(dropdown)
        view.add_item(discord.ui.Button(label="View the Kata", url=link))
        return view

    @commands.command(aliases=["kata"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def challenge(self, ctx: Context, language: str = "python", *, query: str | None = None) -> None:
        """The challenge command pulls a random kata (challenge) from codewars.com.
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
            msg = "This is not a recognized language on codewars.com!"
            raise commands.BadArgument(msg)

        get_kata_link = f"https://codewars.com/kata/search/{language}"
        params = {}

        if query is not None:
            if "," in query:
                query_splitted = query.split("," if ", " not in query else ", ")

                if len(query_splitted) > 2:
                    msg = "There can only be one comma within the query, separating the difficulty and the query itself."
                    raise commands.BadArgument(
                        msg,
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
        if isinstance(first_kata_id, discord.Embed):
            # We ran into an error when retrieving the website link
            await ctx.send(embed=first_kata_id)
            return

        kata_information = await self.kata_information(first_kata_id)
        if isinstance(kata_information, discord.Embed):
            # Something went wrong when trying to fetch the kata information
            await ctx.send(embed=kata_information)
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
        kata_view = self.create_view(dropdown, f"https://codewars.com/kata/{first_kata_id}")
        original_message: discord.Message = await ctx.send(embed=kata_embed, view=kata_view)
        dropdown.original_message = original_message

        wait_for_kata = await kata_view.wait()
        if wait_for_kata:
            await original_message.edit(embed=kata_embed, view=None)

    @commands.command(name="bin")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def bin(self, ctx: Context, *, code: str) -> None:
        """Upload your code/text/document to a mystbin service. Will be there for 30 days."""
        if len(code) < 10:
            msg = "Your code is too short to be uploaded to a mystbin service."
            raise commands.BadArgument(msg)

        b = await self.bot.mystbin.create_paste(filename="file.txt", content=code)
        await ctx.send(f"Your code has been uploaded to {b.url}")

    kontests_cache = {}

    @commands.command(name="kontests")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def kontests(self, ctx: Context, platform: str | None = None) -> None:
        """Get the upcoming contests on various competitive programming platforms."""

        if random() < 0.1:
            await ctx.send("From Owner: This command is still in development. Please be patient.")

        available_platforms = {"hackerearth", "hackerrank", "codeforces", "atcoder"}
        if platform is None:
            msg = "Please provide a platform to get the upcoming contests for."
            msg += f"\n\nAvailable platforms: {', '.join(available_platforms)}"
            raise commands.BadArgument(msg)

        fuzzy_match = rapidfuzz.process.extractOne(platform.lower(), available_platforms, score_cutoff=85)
        if not fuzzy_match:
            msg = "This is not a recognized platform for competitive programming!"
            raise commands.BadArgument(msg)

        platform = fuzzy_match[0]
        mapping = {
            "hackerearth": self.kontest_hackerearth,
            "hackerrank": self.kontest_hackerrank,
            "codeforces": self.kontest_codeforces,
            "atcoder": self.kontest_atcoder,
        }

        kontests = await mapping[platform]()
        if not kontests:
            await ctx.send(f"No upcoming contests found for {platform.capitalize()}.")

        await ctx.paginate(kontests, per_page=6)

    async def kontest_hackerearth(self) -> list:
        if "hackerearth" not in self.kontests_cache:
            hackerearth = HackerEarth()
            await hackerearth.fetch(self.bot.http_session)
            self.kontests_cache["hackerearth"] = hackerearth.contests

        contests = self.kontests_cache["hackerearth"]

        return [
            f"""ID: *{contest.id}* | **[{contest.title}]({contest.url})** | {contest.status}
{contest.description}
`Start:` {discord.utils.format_dt(contest.start_time, "R")}
`End  :` {discord.utils.format_dt(contest.end_time, "R")}
"""
            for contest in contests
        ]

    async def kontest_hackerrank(self) -> list:
        if "hackerrank" not in self.kontests_cache:
            hackerrank = HackerRank()
            await hackerrank.fetch(self.bot.http_session)
            self.kontests_cache["hackerrank"] = hackerrank.contests

        contests = self.kontests_cache["hackerrank"]

        return [
            f"""ID: *{contest.id}* | **[{contest.name}]({contest.url})** | {'ENDED' if contest.ended else 'UPCOMING/ONGOING'}
{contest.description}
`Start:` {discord.utils.format_dt(contest.start_time, "R")}
`End  :` {discord.utils.format_dt(contest.end_time, "R")}
"""
            for contest in contests
        ]

    async def kontest_codeforces(self) -> list:
        if "codeforces" not in self.kontests_cache:
            codeforces = CodeForces()
            await codeforces.fetch(self.bot.http_session)
            self.kontests_cache["codeforces"] = codeforces.contests

        contests = self.kontests_cache["codeforces"]

        return [
            f"""ID: *{contest.id}* | **[{contest.name}]({contest.website_url})** | {contest.phase} | {contest.difficulty}
{contest.description}
`Start:` {discord.utils.format_dt(contest.start_time, "R") if contest.start_time else 'TBA'}
`Time :` {contest.duration_seconds // 60} Minutes
"""
            for contest in contests
        ]

    async def kontest_atcoder(self) -> list:
        if "atcoder" not in self.kontests_cache:
            atcoder = AtCoder()
            await atcoder.fetch(self.bot.http_session)
            self.kontests_cache["atcoder"] = atcoder.contests

        contests = self.kontests_cache["atcoder"]

        return [
            f"""ID: NA | **[{contest.name}]({contest.url})**
*Description not available*
`Start:` {discord.utils.format_dt(contest.start_time, "R")}
"""
            for contest in contests
        ]
