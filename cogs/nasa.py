import os

from datetime import datetime
import discord, aiohttp
from discord.ext import commands
import urllib.parse

from utilities.paginator import Paginator
from utilities.checks import user_premium_cd

from core import Cog, Parrot, Context

NASA_KEY = os.environ['NASA_KEY']


class NASA(Cog, name='nasa'):
    '''Incridible NASA API Integration'''
    def __init__(self, bot: Parrot):
        self.bot = bot

    @commands.command(aliases=['sat', 'satelite'])
    @commands.guild_only()
    @user_premium_cd()
    @commands.bot_has_permissions(embed_links=True)
    async def nasa(self, ctx: Context, longitute: float, latitude: float,
                   date: str):
        """Satelite Imagery - NASA. Date must be in "YYYY-MM-DD" format"""

        link = f'https://api.nasa.gov/planetary/earth/imagery?lon={longitute}&lat={latitude}&date={date}&dim=0.15&api_key={NASA_KEY}'

        embed = discord.Embed(title='Earth',
                              colour=discord.Colour.blue(),
                              timestamp=datetime.utcnow())
        embed.set_image(url=f"{link}")
        embed.set_thumbnail(
            url=
            'https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png')
        embed.set_footer(text=f"{ctx.author.name}")

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @user_premium_cd()
    @commands.bot_has_permissions(embed_links=True)
    async def apod(self, ctx: Context):
        '''Asteroid Picture of the Day'''
        link = f'https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}'

        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        title = res['title']
        expln = res['explanation']
        #authr = res['copyright']
        date_ = res['date']
        if res['media_type'] == "image":
            image = res['media_type']

        embed = discord.Embed(title=f"Astronomy Picture of the Day: {title}",
                              description=f"{expln}")
        if res['media_type'] == "image":
            image = res['url']
            embed.set_image(url=f"{image}")
        #embed.set_author(name=f"Author: {authr}")
        embed.set_footer(text=f"{date_}")

        await ctx.send(embed=embed)

    @commands.command(aliases=['earth'])
    @commands.guild_only()
    @user_premium_cd()
    @commands.bot_has_permissions(embed_links=True)
    async def epic(self, ctx: Context, date: str):
        '''Earth Polychromatic Imaging Camera. Date must be in "YYYY-MM-DD" format'''
        s_link = f'https://epic.gsfc.nasa.gov/api/images.php?date={date}'

        async with aiohttp.ClientSession() as session:
            async with session.get(s_link) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        em_list = []
        for index in range(0, len(res)):
            caption = res[index]['caption']
            im = res[index]['image']
            lat = res[index]['centroid_coordinates']['lat']
            lon = res[index]['centroid_coordinates']['lon']
            link = 'https://epic.gsfc.nasa.gov/epic-archive/jpg/' + im + '.jpg'
            embed = discord.Embed(title=f'{caption}',
                                  colour=discord.Colour.blue(),
                                  description=f'Lat: {lat} | Lon: {lon}',
                                  timestamp=datetime.utcnow())
            embed.set_image(url=f"{link}")
            embed.set_footer(
                text=f"Page {index}/{len(res)} | {ctx.author.name}")
            em_list.append(embed)
        paginator = Paginator(pages=em_list, timeout=60.0)

        await paginator.start(ctx)

    @commands.command(aliases=['finda', 'asteroid'])
    @commands.guild_only()
    @user_premium_cd()
    @commands.bot_has_permissions(embed_links=True)
    async def findasteroid(self, ctx: Context, start: str, end: str):
        '''You can literally find any asteroid in the space by date. Date must be in "YYYY-MM-DD" format'''
        link = f'https://api.nasa.gov/neo/rest/v1/feed?start_date={start}&end_date={end}&api_key={NASA_KEY}'

        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        em_list = []

        for date in res['near_earth_objects']:
            for index in range(0, len(date)):
                link_self = date[index]['nasa_jpl_url']
                name_end = date[index]['name']
                id_end = date[index]['neo_reference_id']
                dia = round(
                    float(date[index]['estimated_diameter']['meters']
                          ['estimated_diameter_min']))
                danger = date[index]['is_potentially_hazardous_asteroid']
                approach_date = date[index]['close_approach_data'][0][
                    'close_approach_date']
                velocity = date[index]['close_approach_data'][0][
                    'relative_velocity']['kilometers_per_hour']
                miss_dist = date[index]['close_approach_data'][0][
                    'miss_distance']['kilometers']
                orbiting = date[index]['close_approach_data'][0][
                    'orbiting_body']
                is_sentry_object = date[index]['is_sentry_object']

                embed = discord.Embed(
                    description=f"Retriving data from {start} to {end}",
                    url=f"{link_self}",
                    timestamp=datetime.utcnow())
                embed.add_field(name="Asteroid Name:",
                                value=f"{name_end}",
                                inline=True)
                embed.add_field(name="Asteroid ID:",
                                value=f"{id_end}",
                                inline=True)
                embed.add_field(name="Estimated Diameter:",
                                value=f"{dia} M",
                                inline=True)
                embed.add_field(name="Is Danger?",
                                value=f"{danger}",
                                inline=True)
                embed.add_field(name="Approach Date:",
                                value=f"{approach_date}",
                                inline=True)
                embed.add_field(name="Relative velocity:",
                                value=f"{velocity} KM/hr",
                                inline=True)
                embed.add_field(name="Miss Distance:",
                                value=f"{miss_dist} KM",
                                inline=True)
                embed.add_field(name="Orbiting:",
                                value=f"{orbiting}",
                                inline=True)
                embed.add_field(name="Is sentry?",
                                value=f"{is_sentry_object}",
                                inline=True)
                embed.set_thumbnail(
                    url=
                    'https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png'
                )
                embed.set_footer(
                    text=f"Page {index}/{len(date)} | {ctx.author.name}")

        paginator = Paginator(pages=em_list, timeout=60.0)

        await paginator.start(ctx)

    @commands.command(aliases=['findaid', 'asteroidid'])
    @commands.guild_only()
    @user_premium_cd()
    @commands.bot_has_permissions(embed_links=True)
    async def findasteroididid(self, ctx: Context, id: int):
        '''Find any asteroid in the space by ID. "$help findaid" for syntax'''
        link = f'https://api.nasa.gov/neo/rest/v1/neo/{id}?api_key={NASA_KEY}'

        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        name = res['name']
        link_self = res['nasa_jpl_url']

        dia = round(
            res['estimated_diameter']['meters']['estimated_diameter_min'])
        danger = res['is_potentially_hazardous_asteroid']
        sentry = res['is_sentry_object']
        orbitaldata = res['orbital_data']['orbit_class'][
            'orbit_class_description']
        orbital_ran = res['orbital_data']['orbit_class']['orbit_class_range']
        last_obs = res['orbital_data']['last_observation_date']
        orbit_sp = res['close_approach_data'][0]['relative_velocity'][
            'kilometers_per_hour']
        orbital_p = res['close_approach_data'][0]['orbiting_body']
        embed = discord.Embed(
            title=f"Asteroid Name: {name}",
            url=f"{link_self}",
            description=f"{orbitaldata}\nRange: {orbital_ran}")
        embed.add_field(name="Estimated Diameter:",
                        value=f"{dia} M",
                        inline=True)
        embed.add_field(name="Is Danger?", value=f"{danger}", inline=True)
        embed.add_field(name="Is sentry?", value=f"{sentry}", inline=True)
        embed.add_field(name="Relative velocity:",
                        value=f"{orbit_sp} KM/hr",
                        inline=True)
        embed.add_field(name="Orbiting:", value=f"{orbital_p}", inline=True)
        embed.add_field(name="Last observation date:",
                        value=f"{last_obs}",
                        inline=True)
        embed.set_thumbnail(
            url=
            'https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png')
        embed.set_footer(text=f"{ctx.author.name}")

        await ctx.send(embed=embed)

    @commands.command(aliases=['mrp'])
    @commands.guild_only()
    @user_premium_cd()
    @commands.bot_has_permissions(embed_links=True)
    async def mars(self, ctx: Context, date: str):
        """Mars Rovers Pictures. Date must be in "YYYY-MM-DD" format"""
        link = f'https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/photos?earth_date={date}&api_key={NASA_KEY}'

        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        em_list = []

        for index in range(0, len(res['photos'])):
            img = res['photos'][index]['img_src']
            date_ = res['photos'][index]['earth_date']
            status = res['photos'][index]['rover']['status'].capitalize()

            embed = discord.Embed(
                title="Mars Rover Photos",
                description=f"Status: {status} | Date of imagery: {date_}",
                timestamp=datetime.utcnow())
            embed.set_image(url=f"{img}")
            embed.set_footer(
                text=f"Page {index}/{len(res['photos'])} | {ctx.author.name}")

        paginator = Paginator(pages=em_list, timeout=60.0)

        await paginator.start(ctx)

    @commands.command(aliases=['nsearch', 'ns'])
    @commands.guild_only()
    @user_premium_cd()
    @commands.bot_has_permissions(embed_links=True)
    async def nasasearch(self, ctx: Context, *, string: str):
        '''NASA Image and Video Library'''
        new_text = urllib.parse.quote(string)
        link = 'https://images-api.nasa.gov/search?q=' + new_text
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return


#     if res['collection']['metadata']['total_hits'] == 0:
#       await ctx.send(f'{ctx.author.mention} could not find **{string}** in NASA Image and Video Library.')

#     _1_des = res['collection']['items'][0]['data'][0]['description'][:1000:]
#     _1_mdT = res['collection']['items'][0]['data'][0]['media_type']
#     _1_tit = res['collection']['items'][0]['data'][0]['title']
#     _1_pre = res['collection']['items'][0]['links'][0]['href']

#     _2_des = res['collection']['items'][1]['data'][0]['description'][:1000:]
#     _2_mdT = res['collection']['items'][1]['data'][0]['media_type']
#     _2_tit = res['collection']['items'][1]['data'][0]['title']
#     _2_pre = res['collection']['items'][1]['links'][0]['href']

#     _3_des = res['collection']['items'][2]['data'][0]['description'][:1000:]
#     _3_mdT = res['collection']['items'][2]['data'][0]['media_type']
#     _3_tit = res['collection']['items'][2]['data'][0]['title']
#     _3_pre = res['collection']['items'][2]['links'][0]['href']

#     embed = discord.Embed(title="NASA Image and Video Library", colour=discord.Colour.blue())
#     embed.add_field(name=f"[1] {_1_tit}", value=f"{_1_des}", inline=False)
#     embed.add_field(name=f"[2] {_2_tit}", value=f"{_2_des}", inline=False)
#     embed.add_field(name=f"[3] {_3_tit}", value=f"{_3_des}", inline=False)

#     await ctx.send(f'{ctx.author.mention} Found three results, media type:\n[1] **{_1_mdT}**\n[2] **{_2_mdT}**\n[3] **{_3_mdT}**\nFrom NASA Image and Video Library database. You may use the index [1,2,3] to get the media files.')
#     await ctx.send(embed=embed)

#     ans = []
#     def check(m):
#       return m.author == ctx.author and m.channel == ctx.channel

#     message = await self.bot.wait_for('message', timeout=60, check=check)

#     ans.append(message.content)

# #		ind_ = ans[0]

#     #pre_ = requests.get(_1_pre)
#     col = res['collection']['items'][int(ans[0])]['href']
#     print(col, "\n")
#     req = requests.get(col)
#     res = req.json()
#     print(res, "\n")

#     try:
#       for i in range(len(res[0])):
#           if ".mp4" in res[i]:
#             url = res[i]
#             print(url)
#             await ctx.send(f'{url}')
#             break
#     except:
#       pass

#     try:
#       for i in range(len(res[0])):
#           if ".jpg" in res[i]:
#             url = res[i]
#             await ctx.send(f'{url}')
#             break
#     except:
#       pass


def setup(bot):
    bot.add_cog(NASA(bot))
