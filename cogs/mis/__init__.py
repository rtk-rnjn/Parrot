from discord.ext import commands
from utilities.youtube_search import YoutubeSearch
import urllib.parse, aiohttp, discord, re, editdistance, wikipedia, json, ttg, datetime, typing, os, inspect
from utilities.paginator import Paginator
from discord import Embed
from core import Parrot, Context, Cog

invitere = r"(?:https?:\/\/)?discord(?:\.gg|app\.com\/invite)?\/(?:#\/)([a-zA-Z0-9-]*)"
invitere2 = r"(http[s]?:\/\/)*discord((app\.com\/invite)|(\.gg))\/(invite\/)?(#\/)?([A-Za-z0-9\-]+)(\/)?"

google_key = os.environ['GOOGLE_KEY']
cx = os.environ['GOOGLE_CX']

class misc(Cog):
    """Those commands which can't be listed"""
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.snipes = {}

        @bot.listen('on_message_delete')
        async def on_message_delete(msg):
            if msg.author.bot:
                return
            self.snipes[msg.channel.id] = msg

        @bot.listen('on_message_edit')
        async def on_message_edit(before, after):
            if before.author.bot or after.author.bot:
                return  # DEPARTMENT OF REDUNDANCY DEPARTMENT
            if (editdistance.eval(before.content, after.content) >=
                    10) and (len(before.content) > len(after.content)):
                self.snipes[before.channel.id] = [before, after]

    def sanitise(self, string):
        if len(string) > 1024:
            string = string[0:1021] + "..."
        string = re.sub(invitere2, '[INVITE REDACTED]', string)
        return string

    @commands.command(aliases=['bigemote'])
    @commands.has_permissions(embed_links=True)
    @commands.bot_has_permissions(embed_links=True, manage_messages=True)
    @Context.with_type
    async def bigemoji(self, ctx: Context, *, emoji: discord.Emoji):
        """
				To view the emoji in bigger form
				"""
        await ctx.message.delete()
        await ctx.send(emoji.url)

    @commands.command(aliases=['calc', 'cal'])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def calculator(self, ctx: Context, *, text: str):
        """
				This is basic calculator with all the expression supported. Syntax is similar to python math module.
				"""
        new_text = urllib.parse.quote(text)
        link = 'http://twitch.center/customapi/math?expr=' + new_text

        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.text()
                else:
                    return
        embed = discord.Embed(title="Calculated!!",
                              description=f'```ini\n[Answer is: {res}]```',
                              timestamp=datetime.datetime.utcnow())
        embed.set_footer(text=f"{ctx.author.name}")

        await ctx.reply(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def maths(self, ctx: Context, operation: str, *, expression: str):
        """
				Another calculator but quite advance one

				NOTE: Available operation - Simplify, Factor, Derive, Integrate, Zeroes, Tangent, Area, Cos, Sin, Tan, Arccos, Arcsin, Arctan, Abs, Log
				For more detailed use, visit: `https://github.com/aunyks/newton-api/blob/master/README.md`
				"""
        new_expression = urllib.parse.quote(expression)
        link = 'https://newton.now.sh/api/v2/' + operation + '/' + new_expression
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return await ctx.reply(
                        f"{ctx.author.mention} invalid **{expression}** or either **{operation}**"
                    )
        result = res['result']
        embed = discord.Embed(title="Calculated!!",
                              description=f"```ini\n[Answer is: {result}]```",
                              timestamp=datetime.datetime.utcnow())
        await ctx.reply(embed=embed)

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    @Context.with_type
    async def news(self, ctx: Context, nat: str):
        """This command will fetch the latest news from all over the world."""

        key = os.environ['NEWSKEY']

        link = 'http://newsapi.org/v2/top-headlines?country=' + nat + '&apiKey=' + key
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.json()

        if res['totalResults'] == 0:
            return await ctx.reply(
                f"{ctx.author.mention} :\ **{nat}** is nothing, please provide a valid country code."
            )
        em_list = []
        for data in range(0, len(res['articles'])):

            source = res['articles'][data]['source']['name']
            # url = res['articles'][data]['url']
            author = res['articles'][data]['author']
            title = res['articles'][data]['title']
            description = res['articles'][data]['description']
            img = res['articles'][data]['urlToImage']
            content = res['articles'][data]['content']
            if not content:
                content = "N/A"
            # publish = res['articles'][data]['publishedAt']

            embed = Embed(title=f'{title}',
                          description=f'{description}',
                          timestamp=datetime.datetime.utcnow())
            embed.add_field(name=f'{source}', value=f'{content}')
            embed.set_image(url=f'{img}')
            embed.set_author(name=f'{author}')
            embed.set_footer(text=f'Page {data+1}/{len(res["articles"])}')
            em_list.append(embed)

        paginator = Paginator(pages=em_list, timeout=60.0)
        await paginator.start(ctx)

    @commands.command(name="search", aliases=['googlesearch', 'google'])
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def search(self, ctx: Context, *, search: str):
        """
				Simple google search Engine.
				"""
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

        searchInfoTime = round(json_['searchInformation']['searchTime'])
        context = json_['context']['title']
        pages = []

        embed = discord.Embed(
            title=f"{context}",
            description=
            f"```\nSEARCH ENGINE: GOOGLE\nTIME TAKEN   : {searchInfoTime}```",
            timestamp=datetime.datetime.utcnow())
        embed.set_footer(text=f"{ctx.author.name}")
        embed.set_thumbnail(
            url=
            "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Google_%22G%22_Logo.svg/1200px-Google_%22G%22_Logo.svg.png"
        )

        pages.append(embed)

        for item in json_['items']:
            title = item['title']
            link = item['link']
            displaylink = item['displayLink']
            snippet = item['snippet']
            try:
                img = item['pagemap']['cse_thumbnail'][0]['src']
            except KeyError:
                img = None
            em = discord.Embed(title=f"{title}",
                               description=f"{displaylink}```\n{snippet}```",
                               timestamp=datetime.datetime.utcnow(),
                               url=f"{link}")
            em.set_footer(text=f"{ctx.author.name}")
            if not img: pass
            else: em.set_thumbnail(url=img)
            pages.append(em)

        paginator = Paginator(pages=pages, timeout=60.0)
        await paginator.start(ctx)

    @commands.command()
    @commands.bot_has_permissions(read_message_history=True, embed_links=True)
    @Context.with_type
    async def snipe(self, ctx: Context):
        """
				"Snipes" someone\'s message that\'s deleted
				"""
        try:
            snipe = self.snipes[ctx.channel.id]
        except KeyError:
            return await ctx.send(
                f'{ctx.author.mention} no snipes in this channel!')
        if snipe is None:
            return await ctx.send(
                f'{ctx.author.mention} no snipes in this channel!')
        # there's gonna be a snipe after this point
        emb = discord.Embed()
        if type(snipe) == list:  # edit snipe
            emb.set_author(name=str(snipe[0].author),
                           icon_url=snipe[0].author.display_avatar.url)
            emb.colour = snipe[0].author.colour
            emb.add_field(name='Before',
                          value=self.sanitise(snipe[0].content),
                          inline=False)
            emb.add_field(name='After',
                          value=self.sanitise(snipe[1].content),
                          inline=False)
            emb.timestamp = snipe[0].created_at
        else:  # delete snipe
            emb.set_author(name=str(snipe.author),
                           icon_url=snipe.author.display_avatar.url)
            emb.description = self.sanitise(snipe.content)
            emb.colour = snipe.author.colour
            emb.timestamp = snipe.created_at
            emb.set_footer(text=f'Message sniped by {str(ctx.author)}',
                           icon_url=ctx.author.display_avatar.url)
        await ctx.reply(embed=emb)
        self.snipes[ctx.channel.id] = None

    @commands.command(aliases=['trutht', 'tt', 'ttable'])
    @Context.with_type
    async def truthtable(self, ctx: Context, *, data: commands.clean_content):
        """A simple command to generate Truth Table of given data. Make sure you use proper syntax.
           Syntax:
		   Truthtable -var *variable1*, *variable2*, *variable3* ... -con *condition1*, *condition2*, *condition3* ...`
           (Example: `tt -var a, b -con a and b, a or b`)
		"""
        data = data.split("-")
        if data[-2][:3:] == "var":
            var = data[-2][4::].replace(" ", "").split(",")
        if data[-1][:3:] == "var":
            var = data[-1][4::].replace(" ", "").split(",")

        if data[-1][:3:] == "con": con = data[-1][4::].split(",")
        if data[-2][:3:] == "con": con = data[-2][4::].split(",")

        table = ttg.Truths(var, con, ints=False).as_prettytable()

        await ctx.reply(f"```\n{table}\n```")

    @commands.command(aliases=['w'])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def weather(self, ctx: Context, *, location: str):
        """Weather API, for current weather forecast, supports almost every city."""

        appid = os.environ['WEATHERID']

        loc = urllib.parse.quote(location)
        link = 'https://api.openweathermap.org/data/2.5/weather?q=' + loc + '&appid=' + appid

        loc = loc.capitalize()
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return await ctx.reply(
                        f"{ctx.author.mention} no location named, **{location}**"
                    )

        lat = res['coord']['lat']
        lon = res['coord']['lon']

        weather = res['weather'][0]['main']

        max_temp = res['main']['temp_max'] - 273.5
        min_temp = res['main']['temp_min'] - 273.5

        press = res['main']['pressure'] / 1000

        humidity = res['main']['humidity']

        visiblity = res['visibility']
        wind_speed = res['wind']['speed']

        loc_id = res['id']
        country = res['sys']['country']

        embed = discord.Embed(title=f"Weather Menu of: {loc}",
                              description=f"Weather: {weather}",
                              timestamp=datetime.datetime.utcnow())
        embed.add_field(name="Latitude", value=f"{lat} Deg", inline=True)
        embed.add_field(name="Longitude", value=f"{lon} Deg", inline=True)
        embed.add_field(name="Humidity", value=f"{humidity} g/m³", inline=True)
        embed.add_field(name="Maximum Temperature",
                        value=f"{round(max_temp)} C Deg",
                        inline=True)
        embed.add_field(name="Minimum Temperature",
                        value=f"{round(min_temp)} C Deg",
                        inline=True)
        embed.add_field(name="Pressure", value=f"{press} Pascal", inline=True)

        embed.add_field(name="Visibility", value=f"{visiblity} m", inline=True)
        embed.add_field(name="Wind Speed",
                        value=f"{wind_speed} m/s",
                        inline=True)
        embed.add_field(name="Country", value=f"{country}", inline=True)
        embed.add_field(name="Loaction ID",
                        value=f"{loc}: {loc_id}",
                        inline=True)
        embed.set_footer(text=f"{ctx.author.name}")

        await ctx.reply(embed=embed)

    @commands.command(aliases=['wiki'])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def wikipedia(self, ctx: Context, *, text: str):
        """Web articles from Wikipedia."""
        link = str(wikipedia.page(text).url)
        try:
            summary = str(wikipedia.summary(text,
                                            sentences=3)).replace("\n", "")
        except wikipedia.exceptions.DisambiguationError as e:
            return await ctx.reply(
                f'{ctx.author.mention} please provide more arguments, like {e.options[0]}'
            )
        title = str(wikipedia.page(text).title)
        image = wikipedia.page(text).images[0]

        embed = discord.Embed(title=title,
                              description=f"Summary: {summary}",
                              url=link,
                              color=ctx.author.color)
        embed.set_footer(text=f"{ctx.author.name}")
        embed.set_image(url=image)

        await ctx.reply(embed=embed)

    @commands.command(aliases=['yt'])
    @commands.bot_has_permissions(embed_links=True)
    @commands.is_nsfw()
    @Context.with_type
    async def youtube(self, ctx: Context, *, query: str):
        """
		Search for videos on YouTube.
		"""
        results = await YoutubeSearch(query, max_results=5).to_json()
        main = json.loads(results)

        em_list = []

        for i in range(0, len(main['videos'])):
            _1_title = main['videos'][i]['title']
            _1_descr = main['videos'][i]['long_desc']
            _1_chann = main['videos'][i]['channel']
            _1_views = main['videos'][i]['views']
            _1_urlsu = 'https://www.youtube.com' + str(
                main['videos'][i]['url_suffix'])
            _1_durat = main['videos'][i]['duration']
            _1_thunb = str(main['videos'][i]['thumbnails'][0])
            embed = discord.Embed(title=f"YouTube search results: {query}",
                                  description=f"{_1_urlsu}",
                                  colour=discord.Colour.red())
            embed.add_field(
                name=f"Video title:`{_1_title}`\n",
                value=
                f"Channel:```\n{_1_chann}\n```\nDescription:```\n{_1_descr}\n```\nViews:```\n{_1_views}\n```\nDuration:```\n{_1_durat}\n```",
                inline=False)
            embed.set_thumbnail(
                url=
                'https://cdn4.iconfinder.com/data/icons/social-messaging-ui-color-shapes-2-free/128/social'
                '-youtube-circle-512.png')
            embed.set_image(url=f'{_1_thunb}')
            embed.set_footer(text=f"{ctx.author.name}")
            em_list.append(embed)

        paginator = Paginator(pages=em_list, timeout=60.0)
        await paginator.start(ctx)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def embed(self, ctx: Context, *, data):
        """
				A nice command to make custom embeds, from a `Python Dictionary` or form `JSON`. Provided it is in the format that Discord expects it to be in. You can find the documentation on `https://discord.com/developers/docs/resources/channel#embed-object`.
				"""
        if type(data) is dict:
            await ctx.send(embed=discord.Embed.from_dict(data))
        else:
            try:
                data = json.loads(data)
                await ctx.send(embed=discord.Embed.from_dict(data))
            except Exception:
                pass

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def snowflakeid(self, ctx: Context, *, target: typing.Union[discord.User, discord.Role, discord.Thread, discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Guild, discord.Emoji, discord.Message, discord.Invite, discord.Template, discord.CategoryChannel, discord.DMChannel, discord.GroupChannel]):
        """To get the ID of discord models"""
        embed = discord.Embed(title="Snowflake lookup", color=ctx.author.color, timestamp=datetime.datetime.utcnow())
        await ctx.send(
            f"{ctx.author.mention} {target.id if type(target) is discord.Message else target} is **{type(target)}** of id **{target.id}** created at **{target.created_at}**"
        )

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def snowflaketime(self, ctx: Context, snowflake1: int,
                            snowflake2: int):
        """Get the time difference in seconds, between two discord SnowFlakes"""
        first = discord.utils.snowflake_time(snowflake1)
        second = discord.utils.snowflake_time(snowflake2)

        if snowflake2 > snowflake1:
            timedelta = second - first
        else:
            timedelta = first - second

        await ctx.send(
            f"{ctx.author.mention} total seconds between **{snowflake1}** and **{snowflake2}** is **{timedelta.total_seconds()}**"
        )

    @commands.command(aliases=['src'])
    @Context.with_type
    async def source(self, ctx: Context, branch: str=None, *, command: str = None):
        """Displays my full source code or for a specific command.
        """
        source_url = 'https://github.com/ritik0ranjan/Parrot'
        branch = branch or 'main'
        if command is None:
            return await ctx.send(source_url)

        if command == 'help':
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
        else:
            obj = self.bot.get_command(command.replace('.', ' '))
            if obj is None:
                return await ctx.send('Could not find command.')
            src = obj.callback.__code__
            module = obj.callback.__module__
            filename = src.co_filename

        lines, firstlineno = inspect.getsourcelines(src)
    
        location = module.replace('.', '/') + '.py'

        final_url = f'<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>'
        await ctx.send(final_url)

def setup(bot):
    bot.add_cog(misc(bot))
