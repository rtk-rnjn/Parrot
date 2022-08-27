from __future__ import annotations
from datetime import datetime

import hashlib
import inspect
import io
import json
import os
import re
import string
import urllib.parse
from html import unescape
from pathlib import Path
from typing import Any, BinaryIO, Dict, Iterable, List, Literal, Optional, Union

import aiohttp  # type: ignore
import discord
import qrcode  # type: ignore
from cogs.meta.robopage import SimplePages
from core import Cog, Context, Parrot
from discord import Embed
from discord.ext import commands
from PIL import Image
from qrcode.image.styledpil import StyledPilImage  # type: ignore
from qrcode.image.styles.colormasks import (  # type: ignore
    HorizontalGradiantColorMask,
    RadialGradiantColorMask,
    SolidFillColorMask,
    SquareGradiantColorMask,
    VerticalGradiantColorMask,
)
from qrcode.image.styles.moduledrawers import (  # type: ignore
    CircleModuleDrawer,
    GappedSquareModuleDrawer,
    HorizontalBarsDrawer,
    RoundedModuleDrawer,
    SquareModuleDrawer,
    VerticalBarsDrawer,
)
from utilities.converters import convert_bool
from utilities.paginator import PaginationView
from utilities.ttg import Truths
from utilities.youtube_search import YoutubeSearch

from .__flags import TTFlag, SearchFlag
from .__embed_view import EmbedBuilder, EmbedSend, EmbedCancel

invitere = r"(?:https?:\/\/)?discord(?:\.gg|app\.com\/invite)?\/(?:#\/)([a-zA-Z0-9-]*)"
invitere2 = r"(http[s]?:\/\/)*discord((app\.com\/invite)|(\.gg))\/(invite\/)?(#\/)?([A-Za-z0-9\-]+)(\/)?"

google_key: str = os.environ["GOOGLE_KEY"]
cx: str = os.environ["GOOGLE_CX"]

SEARCH_API = "https://en.wikipedia.org/w/api.php"
WIKI_PARAMS = {
    "action": "query",
    "list": "search",
    "prop": "info",
    "inprop": "url",
    "utf8": "",
    "format": "json",
    "origin": "*",
}
WIKI_THUMBNAIL = (
    "https://upload.wikimedia.org/wikipedia/en/thumb/8/80/Wikipedia-logo-v2.svg"
    "/330px-Wikipedia-logo-v2.svg.png"
)
WIKI_SNIPPET_REGEX = r"(<!--.*?-->|<[^>]*>)"
WIKI_SEARCH_RESULT = "**[{name}]({url})**\n{description}\n"

FORMATTED_CODE_REGEX = re.compile(
    r"(?P<delim>(?P<block>```)|``?)"  # code delimiter: 1-3 backticks; (?P=block) only matches if it's a block
    r"(?(block)(?:(?P<lang>[a-z]+)\n)?)"  # if we're in a block, match optional language (only letters plus newline)
    r"(?:[ \t]*\n)*"  # any blank (empty or tabs/spaces only) lines before the code
    r"(?P<code>.*?)"  # extract all code inside the markup
    r"\s*"  # any more whitespace before the end of the code markup
    r"(?P=delim)",  # match the exact same delimiter from the start again
    re.DOTALL | re.IGNORECASE,  # "." also matches newlines, case insensitive
)

LATEX_API_URL = "https://rtex.probablyaweb.site/api/v2"

THIS_DIR = Path(__file__).parent
CACHE_DIRECTORY = THIS_DIR / "_latex_cache"
CACHE_DIRECTORY.mkdir(exist_ok=True)
TEMPLATE = string.Template(Path("extra/latex_template.txt").read_text())

BG_COLOR = (54, 57, 63, 255)
PAD = 10

with open("extra/country.json") as f:
    COUNTRY_CODES = json.load(f)



_SEACH_FLAG_CONVERTERS = {
    "c2off": "c2coff",
    "exact_terms": "exactTerms",
    "exclude_terms": "excludeTerms",
    "file_type": "fileType",
    "filter": "filter",
    "gl": "gl",
    "high_range": "highRange",
    "hl": "hl",
    "hq": "hq",
    "img_color_type": "imgColorType",
    "img_dominant_color": "imgDominantColor",
    "img_size": "imgSize",
    "img_type": "imgType",
    "link_site": "linkSite",
    "low_range": "lowRange",
    "lr": "lr",
    "num": "num",
    "or_terms": "orTerms",
    "q": "q",
    "related_site": "relatedSite",
    "rights": "rights",
    "safe": "safe",
    "search_type": "searchType",
    "site_search_filter": "siteSearchFilter",
    "sort": "sort",
    "start": "start",
}


def get_country_code(country: str) -> str:
    for c, n in COUNTRY_CODES.items():
        if country.lower() in (c.lower(), n.lower()):
            return c


def _prepare_input(text: str) -> str:
    if match := FORMATTED_CODE_REGEX.match(text):
        return match.group("code")
    return text


def _process_image(data: bytes, out_file: BinaryIO) -> None:
    image = Image.open(io.BytesIO(data)).convert("RGBA")
    width, height = image.size
    background = Image.new("RGBA", (width + 2 * PAD, height + 2 * PAD), "WHITE")
    background.paste(image, (PAD, PAD), image)
    background.save(out_file)


class InvalidLatexError(Exception):
    """Represents an error caused by invalid latex."""

    def __init__(self, logs: Optional[str]):
        super().__init__(logs)
        self.logs = logs


def _create_qr(
    text: str,
    *,
    version: Optional[int] = 1,
    board_size: Optional[int] = 10,
    border: Optional[int] = 4,
    **kw,
) -> discord.File:
    qr = qrcode.QRCode(
        version=version,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=board_size,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white", **kw)

    out = io.BytesIO()
    img.save(out, "png")
    out.seek(0)
    return discord.File(out, filename="qr.png")


class QRCodeFlags(
    commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "
):
    board_size: Optional[int] = 10
    border: Optional[int] = 4
    module_drawer: Optional[str] = None
    color_mask: Optional[str] = None


qr_modular = {
    "square": SquareModuleDrawer(),
    "gapped": GappedSquareModuleDrawer(),
    "circle": CircleModuleDrawer(),
    "round": RoundedModuleDrawer(),
    "vertical": VerticalBarsDrawer(),
    "ver": VerticalBarsDrawer(),
    "horizontal": HorizontalBarsDrawer(),
    "hori": HorizontalBarsDrawer(),
}

qr_color_mask = {
    "solid": SolidFillColorMask(),
    "radial": RadialGradiantColorMask(),
    "square": SquareGradiantColorMask(),
    "hor": HorizontalGradiantColorMask(),
    "horizontal": HorizontalGradiantColorMask(),
    "vertical": VerticalGradiantColorMask(),
    "ver": VerticalGradiantColorMask(),
}


class Misc(Cog):
    """Those commands which can't be listed"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.snipes = {}

        self.youtube_search = YoutubeSearch(5)

        @bot.listen("on_message_delete")
        async def on_message_delete(msg):
            if msg.author.bot:
                return
            self.snipes[msg.channel.id] = msg

        @bot.listen("on_message_edit")
        async def on_message_edit(before, after):
            if before.author.bot or after.author.bot:
                return
            if before.content != after.content:
                self.snipes[before.channel.id] = [before, after]

    async def wiki_request(
        self, _: discord.TextChannel, search: str
    ) -> List[str]:
        """Search wikipedia search string and return formatted first 10 pages found."""
        params = {**WIKI_PARAMS, **{"srlimit": 10, "srsearch": search}}
        async with self.bot.http_session.get(url=SEARCH_API, params=params) as resp:
            if resp.status != 200:
                raise commands.BadArgument(f"Wikipedia API {resp.status}")

            raw_data = await resp.json()

            if not raw_data.get("query"):
                raise commands.BadArgument(
                    f"Wikipedia API: {resp.status} {raw_data.get('errors')}"
                )

            lines = []
            if raw_data["query"]["searchinfo"]["totalhits"]:
                for article in raw_data["query"]["search"]:
                    line = WIKI_SEARCH_RESULT.format(
                        name=article["title"],
                        description=unescape(
                            re.sub(WIKI_SNIPPET_REGEX, "", article["snippet"])
                        ),
                        url=f"https://en.wikipedia.org/?curid={article['pageid']}",
                    )
                    lines.append(line)

            return lines

    def sanitise(self, st: str) -> str:
        if len(st) > 1024:
            st = f"{st[:1021]}..."
        st = re.sub(invitere2, "[INVITE REDACTED]", st)
        return st

    async def _generate_image(self, query: str, out_file: BinaryIO) -> None:
        """Make an API request and save the generated image to cache."""
        payload = {"code": query, "format": "png"}
        async with self.bot.http_session.post(
            LATEX_API_URL, data=payload, raise_for_status=True
        ) as response:
            response_json = await response.json()
        if response_json["status"] != "success":
            raise InvalidLatexError(logs=response_json.get("log"))
        async with self.bot.http_session.get(
            f"{LATEX_API_URL}/{response_json['filename']}", raise_for_status=True
        ) as response:
            _process_image(await response.read(), out_file)

    async def _upload_to_pastebin(self, text: str, lang: str = "txt") -> Optional[str]:
        """Uploads `text` to the paste service, returning the url if successful."""
        post = await self.bot.http_session.post(
            "https://hastebin.com/documents", data=text
        )
        if post.status == 200:
            response = await post.text()
            return f"https://hastebin.com/{response[8:-2]}"

        # Rollback bin
        post = await self.bot.http_session.post(
            "https://bin.readthedocs.fr/new", data={"code": text, "lang": lang}
        )
        if post.status == 200:
            return str(post.url)

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
    async def latex(self, ctx: commands.Context, *, query: str) -> None:
        """Renders the text in latex and sends the image."""
        query = _prepare_input(query)
        query_hash = hashlib.md5(query.encode()).hexdigest()
        image_path = CACHE_DIRECTORY / f"{query_hash}.png"
        async with ctx.typing():
            if not image_path.exists():
                try:
                    with open(image_path, "wb") as out_file:
                        await self._generate_image(
                            TEMPLATE.substitute(text=query), out_file
                        )
                except InvalidLatexError as err:
                    embed = discord.Embed(title="Failed to render input.")
                    if err.logs is None:
                        embed.description = "No logs available"
                    else:
                        logs_paste_url = await self._upload_to_pastebin(err.logs)
                        if logs_paste_url:
                            embed.description = f"[View Logs]({logs_paste_url})"
                        else:
                            embed.description = "Couldn't upload logs."
                    await ctx.send(embed=embed)
                    image_path.unlink()
                    return
            await ctx.send(file=discord.File(image_path, "latex.png"))

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="Plus", id=892440360750555136)

    @commands.command(aliases=["bigemote"])
    @commands.has_permissions(embed_links=True)
    @commands.bot_has_permissions(
        embed_links=True,
    )
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def bigemoji(self, ctx: Context, *, emoji: discord.Emoji):
        """To view the emoji in bigger form"""
        await ctx.reply(emoji.url)

    @commands.command(aliases=["calc", "cal"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def calculator(self, ctx: Context, *, text: str = None):
        """This is basic calculator with all the expression supported. Syntax is similar to python math module"""
        if text:
            new_text = urllib.parse.quote(text)
            link = f"http://twitch.center/customapi/math?expr={new_text}"

            r = await self.bot.http_session.get(link)
            embed = discord.Embed(
                title="Calculated!!",
                description=f"```ini\n[Answer is: {await r.text()}]```",
                timestamp=discord.utils.utcnow(),
            )
            embed.set_footer(text=f"{ctx.author.name}")

            await ctx.reply(embed=embed)
        else:
            from cogs.mis.__calc_view import CalculatorView

            await ctx.send(
                embed=discord.Embed(
                    description="```\n \n```",
                    color=ctx.bot.color,
                    timestamp=discord.utils.utcnow(),
                ),
                view=CalculatorView(ctx.author, timeout=120, ctx=ctx, arg=""),
            )

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def firstmessage(self, ctx: Context, *, channel: discord.TextChannel = None):
        """To get the first message of the specified channel"""
        channel = channel or ctx.channel
        async for msg in channel.history(limit=1, oldest_first=True):
            return await ctx.send(
                embed=discord.Embed(
                    title=f"First message in {channel.name}",
                    url=msg.jump_url,
                    description=f"{msg.content}",  # fuck you pycord
                    timestamp=discord.utils.utcnow(),
                ).set_footer(text=f"Message sent by {msg.author}")
            )

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def maths(self, ctx: Context, operation: str, *, expression: str):
        """Another calculator but quite advance one

        Note: Available operation -
            - Simplify
            - Factor
            - Derive
            - Integrate
            - Zeroes
            - Tangent
            - Area
            - Cos
            - Sin
            - Tan
            - Arccos
            - Arcsin
            - Arctan
            - Abs
            - Log
        For more detailed use, visit: `https://github.com/aunyks/newton-api/blob/master/README.md`
        """
        new_expression = urllib.parse.quote(expression)
        link = f"https://newton.now.sh/api/v2/{operation}/{new_expression}"

        r = await self.bot.htt_session.get(link)
        if r.status == 200:
            res = await r.json()
        else:
            return await ctx.reply(
                f"{ctx.author.mention} invalid **{expression}** or either **{operation}**"
            )
        result = res["result"]
        embed = discord.Embed(
            title="Calculated!!",
            description=f"```ini\n[Answer is: {result}]```",
            timestamp=discord.utils.utcnow(),
        )
        await ctx.reply(embed=embed)

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def news(self, ctx: Context, *, nat: str):
        """This command will fetch the latest news from all over the world.

        $news <country_code>
        """
        NEWS_KEY = os.environ["NEWSKEY"]
        nat = get_country_code(nat)
        if not nat:
            return await ctx.reply(
                f"{ctx.author.mention} **{nat}** is not a valid country code."
            )
        link = f"http://newsapi.org/v2/top-headlines?country={nat}&apiKey={NEWS_KEY}"
        r = await self.bot.http_session.get(link)
        res = await r.json()

        if res["status"].upper() != "OK":
            return await ctx.send(f"{ctx.author.mention} something not right!")

        em_list = []
        for data in range(len(res["articles"])):

            source = res["articles"][data]["source"]["name"]
            # url = res['articles'][data]['url']
            author = res["articles"][data]["author"]
            title = res["articles"][data]["title"]
            description = res["articles"][data]["description"]
            img = res["articles"][data]["urlToImage"]
            content = res["articles"][data]["content"] or "N/A"

            # publish = res['articles'][data]['publishedAt']

            embed = Embed(
                title=f"{title}",
                description=f"{description}",
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(name=f"{source}", value=f"{content}")
            embed.set_image(url=f"{img}")
            embed.set_author(name=f"{author}")
            embed.set_footer(text=f"{ctx.author}")
            em_list.append(embed)

        # paginator = Paginator(pages=em_list, timeout=60.0)
        # await paginator.start(ctx)
        await PaginationView(em_list).start(ctx=ctx)

    @commands.group(
        name="search", aliases=["googlesearch", "google"], invoke_without_command=True
    )
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def search(self, ctx: Context, *, search: str):
        """Simple google search Engine"""
        if ctx.invoked_subcommand:
            return
        search = urllib.parse.quote(search)
        safe = "off" if ctx.channel.nsfw else "active"
        url = f"https://www.googleapis.com/customsearch/v1?key={google_key}&cx={cx}&q={search}&safe={safe}"

        response = await self.bot.http_session.get(url)
        json_ = await response.json()
        if response.status != 200:
            return await ctx.reply(
                f"{ctx.author.mention} No results found. `{json_['error']['message']}`"
            )

        pages = []

        for item in json_.get("items", []):
            title = item["title"]
            link = item["link"]
            snippet = item.get("snippet")

            pages.append(
                f"""**[Title: {title}]({link})**
> {snippet}

"""
            )
        if not pages:
            return await ctx.reply(
                f"{ctx.author.mention} No results found.`{urllib.parse.unquote(search)}`"
            )
        page = SimplePages(entries=pages, ctx=ctx, per_page=3)
        await page.start()

    @search.command()
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def search_custom(self, ctx: Context, *, search: SearchFlag):
        """To make custom search request"""
        PAYLOAD = {"q": search.q}
        for k, v in _SEACH_FLAG_CONVERTERS.items():
            if hasattr(search, k):
                PAYLOAD[v] = getattr(search, k)
        if not ctx.channel.nsfw:
            PAYLOAD["safe"] = "active"

        url = "https://www.googleapis.com/customsearch/v1"
        response = await self.bot.http_session.get(url, params=PAYLOAD)

        json_ = await response.json()
        if response.status != 200:
            return await ctx.reply(
                f"{ctx.author.mention} No results found. `{json_['error']['message']}`"
            )
        pages = []

        for item in json_.get("items", []):
            title = item["title"]
            link = item["link"]
            snippet = item.get("snippet")

            pages.append(
                f"""**[Title: {title}]({link})**
> {snippet}

"""
            )
        if not pages:
            return await ctx.reply(
                f"{ctx.author.mention} No results found.`{urllib.parse.unquote(search)}`"
            )
        page = SimplePages(entries=pages, ctx=ctx, per_page=3)
        await page.start()

    @commands.command()
    @commands.bot_has_permissions(read_message_history=True, embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def snipe(self, ctx: Context):
        """Snipes someone's message that's deleted"""
        snipe = self.snipes.get(ctx.channel.id)
        if snipe is None:
            return await ctx.reply(f"{ctx.author.mention} no snipes in this channel!")
        # there's gonna be a snipe after this point
        emb = discord.Embed()
        if isinstance(snipe, Iterable):  # edit snipe
            emb.set_author(
                name=str(snipe[0].author), icon_url=snipe[0].author.display_avatar.url
            )
            emb.colour = snipe[0].author.colour
            emb.add_field(
                name="Before", value=self.sanitise(snipe[0].content), inline=False
            )
            emb.add_field(
                name="After", value=self.sanitise(snipe[1].content), inline=False
            )
            emb.timestamp = snipe[0].created_at
        else:  # delete snipe
            emb.set_author(
                name=str(snipe.author), icon_url=snipe.author.display_avatar.url
            )
            emb.description = f"{self.sanitise(snipe.content)}"  # fuck you pycord
            emb.colour = snipe.author.colour
            emb.timestamp = snipe.created_at
            emb.set_footer(
                text=f"Message sniped by {str(ctx.author)}",
                icon_url=ctx.author.display_avatar.url,
            )
        await ctx.reply(embed=emb)
        self.snipes[ctx.channel.id] = None

    @commands.command(
        aliases=["trutht", "tt", "ttable"],
    )
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def truthtable(self, ctx: Context, *, flags: TTFlag):
        """A simple command to generate Truth Table of given data. Make sure you use proper syntax.
        (Example: `tt --var a, b --con a and b, a or b`)
        ```
        Negation             : not, -, ~
        Logical disjunction  : or
        Logical nor          : nor
        Exclusive disjunction: xor, !=
        Logical conjunction  : and
        Logical NAND         : nand
        Material implication : =>, implies
        Logical biconditional: =
        ```
        """
        table = Truths(
            flags.var.replace(" ", "").split(","),
            flags.con.split(","),
            ascending=flags.ascending,
        )
        main = table.as_tabulate(
            index=False, table_format=flags.table_format, align=flags.align
        )
        await ctx.reply(f"```{flags.table_format}\n{main}\n```")

    @commands.command(aliases=["w"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def weather(self, ctx: Context, *, location: str):
        """Weather API, for current weather forecast, supports almost every city."""
        appid = os.environ["WEATHERID"]

        loc = urllib.parse.quote(location)
        link = (
            "https://api.openweathermap.org/data/2.5/weather?q="
            + loc
            + "&appid="
            + appid
        )

        r = await self.bot.http_session.get(link)
        if r.status == 200:
            res = await r.json()
        else:
            return await ctx.reply(
                f"{ctx.author.mention} no location named, **{location}**"
            )

        embed: discord.Embed = discord.Embed()

        lat = res["coord"]["lat"]
        lon = res["coord"]["lon"]

        if res["weather"]:
            weather = res["weather"][0]["main"]
            description = res["weather"][0]["description"]
            icon = res["weather"][0]["icon"]
            icon_url = f"http://openweathermap.org/img/w/{icon}.png"
            
            embed.set_thumbnail(url=icon_url)
            embed.description = f"{weather}: {description}"
        
        temp = res["main"]["temp"] - 273.15
        feels_like = res["main"]["feels_like"] - 273.15
        humidity = res["main"]["humidity"]
        pressure = res["main"]["pressure"]
        wind_speed = res["wind"]["speed"]
        wind_deg = res["wind"]["deg"]
        cloudiness = res["clouds"]["all"]
        visibliity = res["visibility"]
        sunrise = datetime.fromtimestamp(res["sys"]["sunrise"])
        sunset = datetime.fromtimestamp(res["sys"]["sunset"])
        country = res["sys"]["country"]
        _id = res["id"]
        name = res["name"]

        embed.add_field(name="Temperature", value=f"{temp:.2f}°C")
        embed.add_field(name="Feels Like", value=f"{feels_like:.2f}°C")
        embed.add_field(name="Humidity", value=f"{humidity}%")
        embed.add_field(name="Pressure", value=f"{pressure}hPa")
        embed.add_field(name="Wind Speed", value=f"{wind_speed}m/s")
        embed.add_field(name="Wind Direction", value=f"{wind_deg}°")
        embed.add_field(name="Cloudiness", value=f"{cloudiness}%")
        embed.add_field(name="Visibility", value=f"{visibliity}m")
        embed.add_field(name="Sunrise", value=f"{sunrise.strftime('%H:%M')}")
        embed.add_field(name="Sunset", value=f"{sunset.strftime('%H:%M')}")
        embed.add_field(name="Country", value=f"{country}")
        embed.add_field(name="Name", value=f"{name}")
        embed.set_footer(text=f"{ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        embed.set_author(name=f"{location}: {_id}", icon_url=ctx.author.display_avatar.url)

        await ctx.reply(embed=embed)

    @commands.command(aliases=["wiki"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def wikipedia(self, ctx: Context, *, search: str):
        """Web articles from Wikipedia."""
        contents = await self.wiki_request(ctx.channel, search)

        if contents:
            embed = Embed(title="Wikipedia Search Results", colour=ctx.author.color)
            embed.set_thumbnail(url=WIKI_THUMBNAIL)
            embed.timestamp = discord.utils.utcnow()
            page = SimplePages(entries=contents, ctx=ctx, per_page=3)
            await page.start()
        else:
            await ctx.send(
                "Sorry, we could not find a wikipedia article using that search term."
            )

    @commands.command(aliases=["yt"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.is_nsfw()
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def youtube(self, ctx: Context, *, query: str):
        """Search for videos on YouTube"""
        results = await self.youtube_search.to_json(query)
        main: Dict[str, Any] = json.loads(results)

        em_list = []

        for i in range(len(main["videos"])):
            _1_title = main["videos"][i]["title"]
            _1_descr = main["videos"][i]["long_desc"]
            _1_chann = main["videos"][i]["channel"]
            _1_views = main["videos"][i]["views"]
            _1_urlsu = "https://www.youtube.com" + str(main["videos"][i]["url_suffix"])
            _1_durat = main["videos"][i]["duration"]
            _1_thunb = str(main["videos"][i]["thumbnails"][0])
            embed = discord.Embed(
                title=f"YouTube search results: {query}",
                description=f"{_1_urlsu}",
                colour=discord.Colour.red(),
                url=_1_urlsu,
            )
            embed.add_field(
                name=f"Video title:`{_1_title}`\n",
                value=f"Channel:```\n{_1_chann}\n```\nDescription:```\n{_1_descr}\n```\nViews:```\n{_1_views}\n```\nDuration:```\n{_1_durat}\n```",
                inline=False,
            )
            embed.set_thumbnail(
                url="https://cdn4.iconfinder.com/data/icons/social-messaging-ui-color-shapes-2-free/128/social"
                "-youtube-circle-512.png"
            )
            embed.set_image(url=f"{_1_thunb}")
            embed.set_footer(text=f"{ctx.author.name}")
            em_list.append(embed)

        # paginator = Paginator(pages=em_list, timeout=60.0)
        # await paginator.start(ctx)
        await PaginationView(em_list).start(ctx=ctx)

    @commands.command()
    @commands.has_permissions(embed_links=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def embed(
        self,
        ctx: Context,
        channel: Optional[discord.TextChannel] = None,
        *,
        data: Union[dict, str] = None,
    ):
        """A nice command to make custom embeds, from `JSON`. Provided it is in the format that Discord expects it to be in.
        You can find the documentation on `https://discord.com/developers/docs/resources/channel#embed-object`."""
        channel = channel or ctx.channel
        if channel.permissions_for(ctx.author).embed_links:
            if not data:
                view = EmbedBuilder(ctx, items=[EmbedSend(channel), EmbedCancel()])
                await view.rendor()
                return
            try:
                data = json.loads(data)
                await channel.send(embed=discord.Embed.from_dict(data))
            except Exception as e:
                await ctx.reply(
                    f"{ctx.author.mention} you didn't provide the proper json object. Error raised: {e}"
                )
        else:
            await ctx.reply(
                f"{ctx.author.mention} you don't have Embed Links permission in {channel.mention}"
            )

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def snowflakeid(
        self,
        ctx: Context,
        *,
        target: Union[
            discord.User,
            discord.Member,
            discord.Role,
            discord.Thread,
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            discord.Guild,
            discord.Emoji,
            discord.Invite,
            discord.Template,
            discord.CategoryChannel,
            discord.DMChannel,
            discord.GroupChannel,
        ],
    ):
        """To get the ID of discord models"""
        embed = discord.Embed(
            title="Snowflake lookup",
            color=ctx.author.color,
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="Type", value=f"`{target.__class__.__name__}`", inline=True
        )
        embed.add_field(
            name="Created At",
            value=f"{discord.utils.format_dt(target.created_at)}",
            inline=True,
        )
        embed.add_field(name="ID", value=f"`{target.id}`", inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.reply(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def snowflaketime(self, ctx: Context, snowflake1: int, snowflake2: int):
        """Get the time difference in seconds, between two discord SnowFlakes"""
        first = discord.utils.snowflake_time(snowflake1)
        second = discord.utils.snowflake_time(snowflake2)

        timedelta = second - first if snowflake2 > snowflake1 else first - second
        await ctx.reply(
            f"{ctx.author.mention} total seconds between **{snowflake1}** and **{snowflake2}** is **{timedelta.total_seconds()}**"
        )

    @commands.command(aliases=["src"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def source(self, ctx: Context, *, command: str = None):
        """Displays my full source code or for a specific command."""
        source_url = self.bot.github
        branch = "main"
        if command is None:
            return await ctx.reply(source_url)

        if command == "help":
            src = type(self.bot.help_command)
            module = src.__module__

        else:
            obj = self.bot.get_command(command.replace(".", " "))
            if obj is None:
                return await ctx.reply("Could not find command.")
            src = obj.callback.__code__
            module = obj.callback.__module__

        lines, firstlineno = inspect.getsourcelines(src)

        location = module.replace(".", "/") + ".py"

        final_url = f"<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>"
        await ctx.reply(final_url)

    @commands.group()
    @commands.has_permissions(embed_links=True, add_reactions=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def poll(
        self,
        ctx: Context,
    ):
        """To make polls. Thanks to Strawpoll API"""
        await self.bot.invoke_help_command(ctx)

    @poll.command(name="create")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def create_poll(self, ctx: Context, question: str, *, options: str):
        """To create a poll, options should be seperated by commas"""
        parrot_db = self.bot.mongo["parrot_db"]
        collection = parrot_db["poll"]
        BASE_URL = "https://strawpoll.com/api/poll/"
        options = options.split(",")
        data = {"poll": {"title": question, "answers": options, "only_reg": True}}
        if len(options) > 10:
            return await ctx.reply(
                f"{ctx.author.mention} can not provide more than 10 options"
            )
        poll = await self.bot.http_session.post(
            BASE_URL, json=data, headers={"API-KEY": os.environ["STRAW_POLL"]}
        )

        data = await poll.json()
        _exists = await collection.find_one_and_update(
            {"_id": ctx.author.id},
            {"$set": {"content_id": data["content_id"]}},
            upsert=True,
        )

        msg = await ctx.reply(
            f"Poll created: <https://strawpoll.com/{data['content_id']}>"
        )
        await msg.reply(
            f"{ctx.author.mention} your poll content id is: {data['content_id']}"
        )

    @poll.command(name="get")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def get_poll(self, ctx: Context, content_id: str):
        """To get the poll data"""
        URL = f"https://strawpoll.com/api/poll/{content_id}"

        poll = await self.bot.http_session.get(
            URL, headers={"API-KEY": os.environ["STRAW_POLL"]}
        )
        try:
            data = await poll.json()
        except json.decoder.JSONDecodeError:
            return
        except aiohttp.ContentTypeError:
            return
        embed = discord.Embed(
            title=data["content"]["poll"]["title"],
            description=f"Total Options: {len(data['content']['poll']['poll_answers'])} | Total Votes: {data['content']['poll']['total_votes']}",
            timestamp=discord.utils.utcnow(),
            color=ctx.author.color,
        )
        for temp in data["content"]["poll"]["poll_answers"]:
            embed.add_field(
                name=temp["answer"], value=f"Votes: **{temp['votes']}**", inline=True
            )
        embed.set_footer(text=f"{ctx.author}")
        await ctx.reply(embed=embed)

    @poll.command(name="delete")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def delete_poll(self, ctx: Context, content_id: str):
        """To delete the poll. Only if it's yours"""
        _exists: Dict[
            str, Any
        ] = await self.bot.mongo.parrot_db.poll.collection.find_one(
            {"_id": ctx.author.id}
        )
        if not _exists:
            return
        URL = "https://strawpoll.com/api/content/delete"
        await self.bot.http_session.delete(
            URL,
            data={"content_id": content_id},
            headers={"API-KEY": os.environ["STRAW_POLL"], **self.bot.GLOBAL_HEADERS},
        )
        await ctx.reply(f"{ctx.author.mention} deleted")

    @commands.command(name="orc")
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def ocr(self, ctx: Context, *, link: str = None):
        """To convert image to text"""
        link = link or ctx.message.attachments[0].url
        if not link:
            await ctx.reply(f"{ctx.author.mention} must provide the link")
        try:
            res = await self.bot.http_session.get(link)
        except Exception as e:
            return await ctx.reply(
                f"{ctx.author.mention} something not right. Error raised {e}"
            )
        else:
            json = await res.json()
        if str(json["status"]) != str(200):
            return await ctx.reply(f"{ctx.author.mention} something not right.")
        msg = json["message"][:2000:]
        await ctx.reply(
            embed=discord.Embed(
                description=msg,
                color=ctx.author.color,
                timestamp=discord.utils.utcnow(),
            ).set_footer(text=f"{ctx.author}")
        )

    @commands.command(name="qr", aliases=["createqr", "cqr"])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def qrcode(self, ctx: Context, text: str, *, flags: QRCodeFlags):
        """To generate the QR from the given Text"""
        payload: Dict[str, Any] = {}
        if flags.module_drawer:
            payload["module_drawer"] = qr_modular.get(flags.module_drawer)
        if flags.color_mask:
            payload["color_mask"] = qr_modular.get(flags.color_mask)

        if payload:
            payload["image_factory"] = StyledPilImage
        payload["board_size"] = flags.board_size
        payload["border"] = flags.border
        file = await self.bot.func(_create_qr, text, **payload)
        e = discord.Embed().set_image(url="attachment://qr.png")
        await ctx.reply(embed=e, file=file)

    @commands.command(name="minecraftstatus", aliases=["mcs", "mcstatus"])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def mine_server_status(
        self, ctx: Context, address: str, bedrock: Optional[convert_bool] = False
    ):
        """If you are minecraft fan, then you must be know about servers. Check server status with thi command"""
        if bedrock:
            link = f"https://api.mcsrvstat.us/bedrock/2/{address}"
        else:
            link = f"https://api.mcsrvstat.us/2/{address}"

        res = await self.bot.http_session.get(link)
        data = await res.json()
        try:
            if data["online"]:
                ip = data["ip"]
                port = data["port"]
                motd = "\n".join(data["motd"]["clean"])
                players_max = data["players"]["max"]
                players_onl = data["players"]["online"]
                version = data["version"]
                protocol = data["protocol"]
                hostname = data["hostname"]
        except KeyError:
            return await ctx.reply(f"{ctx.author.mention} no server exists")

        embed = discord.Embed(
            title="SERVER STATUS",
            description=f"IP: {ip}\n```\n{motd}\n```",
            timestamp=discord.utils.utcnow(),
            color=ctx.author.color,
        )
        embed.add_field(name="Hostname", value=hostname, inline=True)
        embed.add_field(name="Max Players", value=players_max, inline=True)
        embed.add_field(name="Player Online", value=players_onl, inline=True)
        embed.add_field(name="Protocol", value=protocol, inline=True)
        embed.add_field(name="Port", value=port, inline=True)
        embed.add_field(name="MC Version", value=version, inline=True)

        embed.set_footer(text=f"{ctx.author}")

        await ctx.send(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def currencies(self, ctx: Context):
        """To see the currencies notations with names"""
        obj = await self.bot.http_session.get("https://api.coinbase.com/v2/currencies")
        data = await obj.json()
        entries = [f"`{temp['id']}` `{temp['name']}`" for temp in data["data"]]
        p = SimplePages(entries, ctx=ctx)
        await p.start()

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def exchangerate(self, ctx: Context, currency: str):
        """To see the currencies notations with names"""
        if len(currency) != 3:
            return await ctx.send(
                f"{ctx.author.mention} please provide a **valid currency!**"
            )
        obj = await self.bot.http_session.get(
            f"https://api.coinbase.com/v2/exchange-rates?currency={currency}"
        )
        data: dict = await obj.json()

        entries = [f"`{i}` `{j}`" for i, j in data["data"]["rates"].items()]
        p = SimplePages(entries, ctx=ctx)
        await p.start()

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def whatis(self, ctx: Context, *, query: str):
        """To get the meaning of the word"""
        if data := await self.bot.mongo.extra.dictionary.find_one({"word": query}):
            return await ctx.channel.send(
                f"**{data['word'].title()}**: {data['meaning'].split('.')[0]}"
            )
        return await ctx.channel.send(
            "No word found, if you think its a mistake then contact the owner."
        )
