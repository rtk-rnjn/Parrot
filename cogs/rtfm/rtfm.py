from __future__ import annotations

from os import system

system('pip install lxml')

# from datetime import datetime
import unicodedata
import os
import re
import sys
import discord
import aiohttp
import hashlib
# import asyncio
from hashlib import algorithms_available as algorithms
# from yaml import safe_load as yaml_load

import urllib.parse
from io import BytesIO

from bs4 import BeautifulSoup
from bs4.element import NavigableString

from core import Parrot, Context, Cog

from discord.ext import commands
# from discord.utils import escape_mentions

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import _ref
import _doc
from _used import typing, get_raw, paste, Refresh, wrapping, prepare_payload, execute_run
# from _tio import Tio

with open("extra/lang.txt") as f:
    languages = f.read()


class RTFM(Cog):
    """To test code and check docs. Thanks to https://github.com/FrenchMasterSword/RTFMbot"""
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.algos = sorted(
            [h for h in hashlib.algorithms_available if h.islower()])

        self.bot.languages = ()

    def get_content(self, tag):
        """Returns content between two h2 tags"""
        bssiblings = tag.next_siblings
        siblings = []
        for elem in bssiblings:
            # get only tag elements, before the next h2
            # Putting away the comments, we know there's
            # at least one after it.
            if type(elem) == NavigableString:
                continue
            # It's a tag
            if elem.name == 'h2':
                break
            siblings.append(elem.text)
        content = '\n'.join(siblings)
        if len(content) >= 1024:
            content = content[:1021] + '...'

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
        "sql": _ref.sql_ref
    }

    # TODO: lua, java, javascript, asm
    documented = {
        'c': _doc.c_doc,
        'cpp': _doc.cpp_doc,
        'haskell': _doc.haskell_doc,
        'python': _doc.python_doc
    }

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name='rtfm', id=893097656375722024)

    @property
    def session(self):
        return self.bot.session

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
            return await ctx.send(embed=discord.Embed(
                description="No such package found in the search query.",
                color=self.bot.color,
            ))

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

        embed = discord.Embed(title=f"{name} PyPi Stats",
                              description=description,
                              color=discord.Color.teal())

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
            return await ctx.send(embed=discord.Embed(
                description="No such package found in the search query.",
                color=0xCC3534,
            ))

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

        repository = (getval("repository",
                             "url").removeprefix("git+").removesuffix(".git"))

        homepage = getval("homepage")
        _license = getval("license")

        em = discord.Embed(title=f"{pkg_name} NPM Stats",
                           description=description,
                           color=0xCC3534)

        em.add_field(name="Author", value=author, inline=True)
        em.add_field(name="Author Email", value=author_email, inline=True)

        em.add_field(name="Latest Version", value=latest_version, inline=False)
        em.add_field(name="License", value=_license, inline=True)

        em.add_field(name="Repository", value=repository, inline=False)
        em.add_field(name="Homepage", value=homepage, inline=True)

        em.set_thumbnail(
            url=
            "https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Npm-logo.svg/800px-Npm-logo.svg.png"
        )

        await ctx.send(embed=em)

    @commands.command(aliases=["crates"])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def crate(self, ctx: Context, arg: str):
        """Get info about a Rust package directly from the Crates.IO Registry"""

        res_raw = await self.get_package(
            f"https://crates.io/api/v1/crates/{arg}")

        res_json = await res_raw.json()

        if res_json.get("errors"):
            return await ctx.send(embed=discord.Embed(
                description="No such package found in the search query.",
                color=0xE03D29,
            ))
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

        em = discord.Embed(title=f"{pkg_name} crates.io Stats",
                           description=description,
                           color=0xE03D29)

        em.add_field(name="Published By", value=publisher, inline=True)
        em.add_field(name="Downloads",
                     value="{:,}".format(downloads),
                     inline=True)

        em.add_field(name="Latest Version", value=latest_version, inline=False)
        em.add_field(name="License", value=_license, inline=True)

        em.add_field(name="Repository", value=repository, inline=False)
        em.add_field(name="Homepage", value=homepage, inline=True)

        em.set_thumbnail(
            url=
            "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/Rust_programming_language_black_logo.svg/2048px-Rust_programming_language_black_logo.svg.png"
        )

        await ctx.send(embed=em)

    @commands.command(help="""$run <language> [--wrapped] [--stats] <code>
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
                      brief='Execute code in a given programming language')
    async def run(self, ctx, *, payload=''):
        """Execute code in a given programming language"""

        if not payload:
            emb = discord.Embed(
                title='SyntaxError',
                description=
                f"Command `run` missing a required argument: `language`",
                colour=0xff0000)
            return await ctx.send(embed=emb)

        no_rerun = True
        language = payload
        lang = None  # to override in 2 first cases

        if ctx.message.attachments:
            # Code in file
            file = ctx.message.attachments[0]
            if file.size > 20000:
                return await ctx.send("File must be smaller than 20 kio.")
            buffer = BytesIO()
            await ctx.message.attachments[0].save(buffer)
            text = buffer.read().decode('utf-8')
            lang = re.split(r'\s+', payload, maxsplit=1)[0]
        elif payload.split(' ')[-1].startswith('link='):
            # Code in a webpage
            base_url = urllib.parse.quote_plus(
                payload.split(' ')[-1][5:].strip('/'), safe=';/?:@&=$,><-[]')

            url = get_raw(base_url)

            async with self.bot.session.get(url) as response:
                if response.status == 404:
                    return await ctx.send('Nothing found. Check your link')
                elif response.status != 200:
                    return await ctx.send(
                        f'An error occurred (status code: {response.status}). Retry later.'
                    )
                text = await response.text()
                if len(text) > 20000:
                    return await ctx.send(
                        'Code must be shorter than 20,000 characters.')
                lang = re.split(r'\s+', payload, maxsplit=1)[0]
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
            except:
                # We deleted the message
                pass

    @commands.command(aliases=['ref'])
    @commands.bot_has_permissions(embed_links=True)
    @typing
    async def reference(self, ctx: Context, language, *, query: str):
        """Returns element reference from given language"""

        lang = language.strip('`')

        if not lang.lower() in self.referred:
            return await ctx.reply(
                f"{lang} not available. See `[p]list references` for available ones."
            )
        await self.referred[lang.lower()](ctx, query.strip('`'))

    @commands.command(aliases=['doc'])
    @commands.bot_has_permissions(embed_links=True)
    @typing
    async def documentation(self, ctx: Context, language, *, query: str):
        """Returns element reference from given language"""

        lang = language.strip('`')

        if not lang.lower() in self.documented:
            return await ctx.reply(
                f"{lang} not available. See `[p]list documentations` for available ones."
            )
        await self.documented[lang.lower()](ctx, query.strip('`'))

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @typing
    async def man(self, ctx: Context, *, page: str):
        """Returns the manual's page for a (mostly Debian) linux command"""

        base_url = f'https://man.cx/{page}'
        url = urllib.parse.quote_plus(base_url, safe=';/?:@&=$,><-[]')

        async with aiohttp.ClientSession() as client_session:
            async with client_session.get(url) as response:
                if response.status != 200:
                    return await ctx.reply(
                        'An error occurred (status code: {response.status}). Retry later.'
                    )

                soup = BeautifulSoup(await response.text(), 'lxml')

                nameTag = soup.find('h2', string='NAME\n')

                if not nameTag:
                    # No NAME, no page
                    return await ctx.reply(
                        f'No manual entry for `{page}`. (Debian)')

                # Get the two (or less) first parts from the nav aside
                # The first one is NAME, we already have it in nameTag
                contents = soup.find_all('nav',
                                         limit=2)[1].find_all('li',
                                                              limit=3)[1:]

                if contents[-1].string == 'COMMENTS':
                    contents.remove(-1)

                title = self.get_content(nameTag)

                emb = discord.Embed(title=title, url=f'https://man.cx/{page}')
                emb.set_author(name='Debian Linux man pages')
                emb.set_thumbnail(
                    url='https://www.debian.org/logos/openlogo-nd-100.png')

                for tag in contents:
                    h2 = tuple(
                        soup.find(
                            attrs={
                                'name': tuple(tag.children)[0].get('href')[1:]
                            }).parents)[0]
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

        if group == 'languages':
            emb = discord.Embed(
                title=f"Available for {group}:",
                description=
                'View them on [tio.run](https://tio.run/#), or in [JSON format](https://tio.run/languages.json)'
            )
            return await ctx.reply(embed=emb)

        if not group in choices:
            emb = discord.Embed(
                title="Available listed commands",
                description=f"`languages`, `{'`, `'.join(choices)}`")
            return await ctx.reply(embed=emb)

        availables = choices[group]
        description = f"`{'`, `'.join([*availables])}`"
        emb = discord.Embed(title=f"Available for {group}: {len(availables)}",
                            description=description)
        await ctx.reply(embed=emb)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def ascii(self, ctx: Context, *, text: str):
        """Returns number representation of characters in text"""

        emb = discord.Embed(title="Unicode convert",
                            description=' '.join(
                                [str(ord(letter)) for letter in text]))
        emb.set_footer(text=f'Invoked by {str(ctx.message.author)}')
        await ctx.reply(embed=emb)

    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def unascii(self, ctx: Context, *, text: str):
        """Reforms string from char codes"""

        try:
            codes = [chr(int(i)) for i in text.split(' ')]
            emb = discord.Embed(title="Unicode convert",
                                description=''.join(codes))
            emb.set_footer(text=f'Invoked by {str(ctx.message.author)}')
            await ctx.reply(embed=emb)
        except ValueError:
            await ctx.reply(
                "Invalid sequence. Example usage : `[p]unascii 104 101 121`")

    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def byteconvert(self, ctx: Context, value: int, unit=None):
        """Shows byte conversions of given value"""
        if not unit: unit = 'Mio'
        units = ('o', 'Kio', 'Mio', 'Gio', 'Tio', 'Pio', 'Eio', 'Zio', 'Yio')
        unit = unit.capitalize()

        if not unit in units and unit != 'O':
            return await ctx.reply(
                f"Available units are `{'`, `'.join(units)}`.")

        emb = discord.Embed(title="Binary conversions")
        index = units.index(unit)

        for i, u in enumerate(units):
            result = round(value / 2**((i - index) * 10), 14)
            emb.add_field(name=u, value=result)

        await ctx.reply(embed=emb)

    @commands.bot_has_permissions(embed_links=True)
    @commands.command(name='hash')
    async def _hash(self, ctx: Context, algorithm, *, text: str):
        """
				Hashes text with a given algorithm
				UTF-8, returns under hexadecimal form
				"""

        algo = algorithm.lower()

        if not algo in self.algos:
            matches = '\n'.join([
                supported for supported in self.algos if algo in supported
            ][:10])
            message = f"`{algorithm}` not available."
            if matches:
                message += f" Did you mean:\n{matches}"
            return await ctx.reply(message)

        try:
            # Guaranteed one
            hash_object = getattr(hashlib, algo)(text.encode('utf-8'))
        except AttributeError:
            # Available
            hash_object = hashlib.new(algo, text.encode('utf-8'))

        emb = discord.Embed(title=f"{algorithm} hash",
                            description=hash_object.hexdigest())
        emb.set_footer(text=f'Invoked by {str(ctx.message.author)}')

        await ctx.reply(embed=emb)

    @commands.command()
    async def charinfo(self, ctx, *, characters: str):
        """
        Shows you information about a number of characters.
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
