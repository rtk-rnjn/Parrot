from __future__ import annotations

from cogs.meta.robopage import SimplePages

from discord.ext import commands
from discord import Embed
from utilities.youtube_search import YoutubeSearch
from utilities.converters import convert_bool
from utilities.paginator import PaginationView

import urllib.parse
import aiohttp
import discord
import re
import ttg
import datetime
import typing
import os
import inspect
import json
from html import unescape

from core import Parrot, Context, Cog

invitere = r"(?:https?:\/\/)?discord(?:\.gg|app\.com\/invite)?\/(?:#\/)([a-zA-Z0-9-]*)"
invitere2 = r"(http[s]?:\/\/)*discord((app\.com\/invite)|(\.gg))\/(invite\/)?(#\/)?([A-Za-z0-9\-]+)(\/)?"

google_key = os.environ["GOOGLE_KEY"]
cx = os.environ["GOOGLE_CX"]

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


class TTFlag(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    var: str
    con: str


class Misc(Cog):
    """Those commands which can't be listed"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.snipes = {}

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
        self, channel: discord.TextChannel, search: str
    ) -> list[str]:
        """Search wikipedia search string and return formatted first 10 pages found."""
        params = WIKI_PARAMS | {"srlimit": 10, "srsearch": search}
        async with self.bot.http_session.get(url=SEARCH_API, params=params) as resp:
            if resp.status != 200:
                raise commands.BadArgument(f"Wikipedia API {resp.status}")

            raw_data = await resp.json()

            if not raw_data.get("query"):
                if error := raw_data.get("errors"):
                    pass
                raise commands.BadArgument(f"Wikipedia API: {resp.status} {error}")

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

    def sanitise(self, string):
        if len(string) > 1024:
            string = string[0:1021] + "..."
        string = re.sub(invitere2, "[INVITE REDACTED]", string)
        return string

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
    async def calculator(self, ctx: Context, *, text: str):
        """This is basic calculator with all the expression supported. Syntax is similar to python math module"""
        new_text = urllib.parse.quote(text)
        link = "http://twitch.center/customapi/math?expr=" + new_text

        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.text()
                else:
                    return
        embed = discord.Embed(
            title="Calculated!!",
            description=f"```ini\n[Answer is: {res}]```",
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_footer(text=f"{ctx.author.name}")

        await ctx.reply(embed=embed)

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
                    timestamp=datetime.datetime.utcnow(),
                ).set_footer(text=f"Message sent by {msg.author}")
            )

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def maths(self, ctx: Context, operation: str, *, expression: str):
        """Another calculator but quite advance one

        Note: Available operation - Simplify, Factor, Derive, Integrate, Zeroes, Tangent, Area, Cos, Sin, Tan, Arccos, Arcsin, Arctan, Abs, Log
        For more detailed use, visit: `https://github.com/aunyks/newton-api/blob/master/README.md`
        """
        new_expression = urllib.parse.quote(expression)
        link = "https://newton.now.sh/api/v2/" + operation + "/" + new_expression
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
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
            timestamp=datetime.datetime.utcnow(),
        )
        await ctx.reply(embed=embed)

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def news(self, ctx: Context, nat: str):
        """This command will fetch the latest news from all over the world."""
        key = os.environ["NEWSKEY"]

        link = "http://newsapi.org/v2/top-headlines?country=" + nat + "&apiKey=" + key
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.json()

        if res["totalResults"] == 0:
            return await ctx.reply(
                f"{ctx.author.mention} **{nat}** is nothing, please provide a valid country code."
            )
        em_list = []
        for data in range(0, len(res["articles"])):

            source = res["articles"][data]["source"]["name"]
            # url = res['articles'][data]['url']
            author = res["articles"][data]["author"]
            title = res["articles"][data]["title"]
            description = res["articles"][data]["description"]
            img = res["articles"][data]["urlToImage"]
            content = res["articles"][data]["content"]
            if not content:
                content = "N/A"
            # publish = res['articles'][data]['publishedAt']

            embed = Embed(
                title=f"{title}",
                description=f"{description}",
                timestamp=datetime.datetime.utcnow(),
            )
            embed.add_field(name=f"{source}", value=f"{content}")
            embed.set_image(url=f"{img}")
            embed.set_author(name=f"{author}")
            embed.set_footer(text=f"{ctx.author}")
            em_list.append(embed)

        # paginator = Paginator(pages=em_list, timeout=60.0)
        # await paginator.start(ctx)
        await PaginationView(em_list).start(ctx=ctx)

    @commands.command(name="search", aliases=["googlesearch", "google"])
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def search(self, ctx: Context, *, search: str):
        """Simple google search Engine"""
        search = urllib.parse.quote(search)

        url = f"https://www.googleapis.com/customsearch/v1?key={google_key}&cx={cx}&q={search}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    json_ = await response.json()
                else:
                    return await ctx.reply(
                        f"{ctx.author.mention} No results found.```\n{search}```"
                    )

        pages = []

        for item in json_["items"]:
            title = item["title"]
            link = item["link"]
            displaylink = item["displayLink"]
            snippet = item.get("snippet")
            try:
                img = item["pagemap"]["cse_thumbnail"][0]["src"]
            except KeyError:
                img = None
            em = discord.Embed(
                title=f"{title}",
                description=f"{displaylink}```\n{snippet}```",
                timestamp=datetime.datetime.utcnow(),
                url=f"{link}",
            )
            em.set_footer(text=f"{ctx.author.name}")
            if not img:
                pass
            else:
                em.set_thumbnail(url=img)
            pages.append(em)

        await PaginationView(pages).start(ctx=ctx)

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
        if type(snipe) is list:  # edit snipe
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

    @commands.command(aliases=["trutht", "tt", "ttable"])
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def truthtable(self, ctx: Context, *, flags: TTFlag):
        """A simple command to generate Truth Table of given data. Make sure you use proper syntax.
        Syntax:
                Truthtable --var *variable1*, *variable2*, *variable3* ... --con *condition1*, *condition2*, *condition3* ...`
        (Example: `tt --var a, b --con a and b, a or b`)
        """
        table = ttg.Truths(
            flags.var.split(","), flags.con.split(","), ints=False
        ).as_prettytable()
        await ctx.reply(f"```\n{table}\n```")

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

        loc = loc.capitalize()
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return await ctx.reply(
                        f"{ctx.author.mention} no location named, **{location}**"
                    )

        lat = res["coord"]["lat"]
        lon = res["coord"]["lon"]

        weather = res["weather"][0]["main"]

        max_temp = res["main"]["temp_max"] - 273.5
        min_temp = res["main"]["temp_min"] - 273.5

        press = res["main"]["pressure"] / 1000

        humidity = res["main"]["humidity"]

        visiblity = res["visibility"]
        wind_speed = res["wind"]["speed"]

        loc_id = res["id"]
        country = res["sys"]["country"]

        embed = discord.Embed(
            title=f"Weather Menu of: {loc}",
            description=f"Weather: {weather}",
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(name="Latitude", value=f"{lat} Deg", inline=True)
        embed.add_field(name="Longitude", value=f"{lon} Deg", inline=True)
        embed.add_field(name="Humidity", value=f"{humidity} g/m³", inline=True)
        embed.add_field(
            name="Maximum Temperature", value=f"{round(max_temp)} C Deg", inline=True
        )
        embed.add_field(
            name="Minimum Temperature", value=f"{round(min_temp)} C Deg", inline=True
        )
        embed.add_field(name="Pressure", value=f"{press} Pascal", inline=True)

        embed.add_field(name="Visibility", value=f"{visiblity} m", inline=True)
        embed.add_field(name="Wind Speed", value=f"{wind_speed} m/s", inline=True)
        embed.add_field(name="Country", value=f"{country}", inline=True)
        embed.add_field(name="Loaction ID", value=f"{loc}: {loc_id}", inline=True)
        embed.set_footer(text=f"{ctx.author.name}")

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
            embed.timestamp = datetime.datetime.utcnow()
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
    async def youtube(
        self, ctx: Context, limit: typing.Optional[int] = None, *, query: str
    ):
        """Search for videos on YouTube"""
        results = await YoutubeSearch(query, max_results=limit or 5).to_json()
        main = json.loads(results)

        em_list = []

        for i in range(0, len(main["videos"])):
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
        channel: typing.Optional[discord.TextChannel] = None,
        *,
        data: typing.Union[dict, str] = None,
    ):
        """A nice command to make custom embeds, from `JSON`. Provided it is in the format that Discord expects it to be in.
        You can find the documentation on `https://discord.com/developers/docs/resources/channel#embed-object`."""
        channel = channel or ctx.channel
        if channel.permissions_for(ctx.author).embed_links:
            if not data:
                return await self.bot.invoke_help_command(ctx)
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
        target: typing.Union[
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
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(
            name="Type", value=f"`{target.__class__.__name__}`", inline=True
        )
        embed.add_field(
            name="Created At",
            value=f"<t:{int(target.created_at.timestamp())}>",
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

        if snowflake2 > snowflake1:
            timedelta = second - first
        else:
            timedelta = first - second

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

    @poll.command(name="create")
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def create_poll(self, ctx: Context, question: str, *, options: str):
        """To create a poll, options should be seperated by commas"""
        parrot_db = await self.bot.db("parrot_db")
        collection = parrot_db["poll"]
        BASE_URL = "https://strawpoll.com/api/poll/"
        options = options.split(",")
        data = {"poll": {"title": question, "answers": options, "only_reg": True}}
        if len(options) > 10:
            return await ctx.reply(
                f"{ctx.author.mention} can not provide more than 10 options"
            )
        async with aiohttp.ClientSession() as session:
            poll = await session.post(
                BASE_URL, json=data, headers={"API-KEY": os.environ["STRAW_POLL"]}
            )

        data = await poll.json()
        _exists = await collection.find_one_and_update(
            {"_id": ctx.author.id}, {"$set": {"content_id": data["content_id"]}}
        )

        if not _exists:
            await collection.insert_one(
                {"_id": ctx.author.id, "content_id": data["content_id"]}
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

        async with aiohttp.ClientSession() as session:
            poll = await session.get(URL, headers={"API-KEY": os.environ["STRAW_POLL"]})
        try:
            data = await poll.json()
        except Exception:
            return
        embed = discord.Embed(
            title=data["content"]["poll"]["title"],
            description=f"Total Options: {len(data['content']['poll']['poll_answers'])} | Total Votes: {data['content']['poll']['total_votes']}",
            timestamp=datetime.datetime.utcnow(),
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
        parrot_db = await self.bot.db("parrot_db")
        collection = parrot_db["poll"]
        _exists = await collection.find_one({"_id": ctx.author.id})
        if not _exists:
            return
        URL = "https://strawpoll.com/api/content/delete"
        async with aiohttp.ClientSession() as session:
            await session.delete(
                URL,
                data={"content_id": content_id},
                headers={"API-KEY": os.environ["STRAW_POLL"]},
            )
        await ctx.reply(f"{ctx.author.mention} deleted")

    @commands.command(name="orc")
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def ocr(self, ctx: Context, *, link: str = None):
        """To convert image to text"""
        if not link:
            link = ctx.message.attachments[0].url
        else:
            await ctx.reply(f"{ctx.author.mention} must provide the link")
        try:
            async with aiohttp.ClientSession() as session:
                res = await session.get(link)
        except Exception as e:
            return await ctx.reply(
                f"{ctx.author.mention} something not right. Error raised {e}"
            )
        json = await res.json()
        if str(json["status"]) != str(200):
            return await ctx.reply(f"{ctx.author.mention} something not right.")
        msg = json["message"][:2000:]
        await ctx.reply(
            embed=discord.Embed(
                description=msg,
                color=ctx.author.color,
                timestamp=datetime.datetime.utcnow(),
            ).set_footer(text=f"{ctx.author}")
        )

    @commands.command(name="qr", aliases=["createqr", "cqr"])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def qrcode(self, ctx: Context, text: str):
        """To generate the QR"""
        text = text.split(" ")[0]
        await ctx.reply(
            embed=discord.Embed(
                color=ctx.author.color, timestamp=datetime.datetime.utcnow()
            )
            .set_image(url=f"https://normal-api.ml/createqr?text={text}")
            .set_footer(text=f"{ctx.author}")
        )

    @commands.command(name="minecraftstatus", aliases=["mcs", "mcstatus"])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def mine_server_status(
        self, ctx: Context, address: str, bedrock: typing.Optional[convert_bool] = False
    ):
        """If you are minecraft fan, then you must be know about servers. Check server status with thi command"""
        if bedrock:
            link = f"https://api.mcsrvstat.us/bedrock/2/{address}"
        else:
            link = f"https://api.mcsrvstat.us/2/{address}"

        async with aiohttp.ClientSession() as session:
            res = await session.get(link)
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
            timestamp=datetime.datetime.utcnow(),
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
        obj = await self.bot.session.get("https://api.coinbase.com/v2/currencies")
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
        obj = await self.bot.session.get(
            f"https://api.coinbase.com/v2/exchange-rates?currency={currency}"
        )
        data: dict = await obj.json()

        entries = [f"`{i}` `{j}`" for i, j in data["data"]["rates"].items()]
        p = SimplePages(entries, ctx=ctx)
        await p.start()
