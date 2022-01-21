from __future__ import annotations

import os

from datetime import datetime
import discord
import aiohttp
from discord.ext import commands

from utilities.paginator import PaginationView
from core import Cog, Parrot, Context

NASA_KEY = os.environ["NASA_KEY"]


class NASA(Cog):
    """Incridible NASA API Integration"""

    def __init__(self, bot: Parrot):
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="nasa", id=892425662864982056)

    @commands.command(aliases=["sat", "satelite"])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def earth(self, ctx: Context, longitute: float, latitude: float, date: str):
        """Satelite Imagery - NASA. Date must be in "YYYY-MM-DD" format"""
        if not -90 <= latitude <= 90:
            return await ctx.reply(
                f"{ctx.author.mention} Invalid latitude range, must be between -90 to 90"
            )
        if not -180 <= latitude <= 180:
            return await ctx.reply(
                f"{ctx.author.mention} Invalid longitude range, must be between -180 to 180"
            )
        link = f"https://api.nasa.gov/planetary/earth/imagery?lon={longitute}&lat={latitude}&date={date}&dim=0.15&api_key={NASA_KEY}"

        embed = discord.Embed(
            title="Earth", colour=discord.Colour.blue(), timestamp=datetime.utcnow()
        )
        embed.set_image(url=f"{link}")
        embed.set_thumbnail(
            url="https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png"
        )
        embed.set_footer(text=f"{ctx.author.name}")

        await ctx.reply(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def apod(self, ctx: Context):
        """Asteroid Picture of the Day"""
        link = f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}"

        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        title = res["title"]
        expln = res["explanation"]
        # authr = res['copyright']
        date_ = res["date"]
        if res["media_type"] == "image":
            image = res["media_type"]

        embed = discord.Embed(
            title=f"Astronomy Picture of the Day: {title} | At: {date_}",
            description=f"{expln}",
            timestamp=datetime.utcnow(),
        )
        if res["media_type"] == "image":
            image = res["url"]
            embed.set_image(url=f"{image}")
        embed.set_thumbnail(
            url="https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png"
        )
        embed.set_footer(text=f"{ctx.author.name}")

        await ctx.reply(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def epic(self, ctx: Context, date: str):
        """Earth Polychromatic Imaging Camera. Date must be in "YYYY-MM-DD" format"""
        s_link = f"https://epic.gsfc.nasa.gov/api/images.php?date={date}"

        async with aiohttp.ClientSession() as session:
            async with session.get(s_link) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        em_list = []
        for index in range(0, len(res)):
            caption = res[index]["caption"]
            im = res[index]["image"]
            lat = res[index]["centroid_coordinates"]["lat"]
            lon = res[index]["centroid_coordinates"]["lon"]
            link = "https://epic.gsfc.nasa.gov/epic-archive/jpg/" + im + ".jpg"
            embed = discord.Embed(
                title=f"{caption}",
                colour=discord.Colour.blue(),
                description=f"Lat: {lat} | Lon: {lon}",
                timestamp=datetime.utcnow(),
            )
            embed.set_image(url=f"{link}")
            embed.set_footer(text=f"Page {index+1}/{len(res)} | {ctx.author.name}")
            embed.set_thumbnail(
                url="https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png"
            )
            em_list.append(embed)
        if not em_list:
            return await ctx.send(f"{ctx.author.mention} no results")
        await PaginationView(em_list).start(ctx=ctx)
        # paginator = Paginator(pages=em_list, timeout=60.0)
        # await paginator.start(ctx)

    @commands.command(aliases=["finda", "asteroid", "neo"])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def findasteroid(self, ctx: Context, start: str, end: str):
        """You can literally find any asteroid in the space by date. Date must be in "YYYY-MM-DD" format"""
        link = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={start}&end_date={end}&api_key={NASA_KEY}"

        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        em_list = []

        for date in res["near_earth_objects"]:
            for index in range(0, len(res["near_earth_objects"][date])):
                link_self = res["near_earth_objects"][date][index]["nasa_jpl_url"]
                name_end = res["near_earth_objects"][date][index]["name"]
                id_end = res["near_earth_objects"][date][index]["neo_reference_id"]
                dia = round(
                    float(
                        res["near_earth_objects"][date][index]["estimated_diameter"][
                            "meters"
                        ]["estimated_diameter_min"]
                    )
                )
                danger = res["near_earth_objects"][date][index][
                    "is_potentially_hazardous_asteroid"
                ]
                approach_date = res["near_earth_objects"][date][index][
                    "close_approach_data"
                ][0]["close_approach_date"]
                velocity = res["near_earth_objects"][date][index][
                    "close_approach_data"
                ][0]["relative_velocity"]["kilometers_per_hour"]
                miss_dist = res["near_earth_objects"][date][index][
                    "close_approach_data"
                ][0]["miss_distance"]["kilometers"]
                orbiting = res["near_earth_objects"][date][index][
                    "close_approach_data"
                ][0]["orbiting_body"]
                is_sentry_object = res["near_earth_objects"][date][index][
                    "is_sentry_object"
                ]

                embed = discord.Embed(
                    title=f"At: {date}",
                    description=f"Retriving data from {start} to {end}",
                    url=f"{link_self}",
                    timestamp=datetime.utcnow(),
                )
                embed.add_field(name="Asteroid Name:", value=f"{name_end}", inline=True)
                embed.add_field(name="Asteroid ID:", value=f"{id_end}", inline=True)
                embed.add_field(
                    name="Estimated Diameter:", value=f"{dia} M", inline=True
                )
                embed.add_field(name="Is Danger?", value=f"{danger}", inline=True)
                embed.add_field(
                    name="Approach Date:", value=f"{approach_date}", inline=True
                )
                embed.add_field(
                    name="Relative velocity:", value=f"{velocity} KM/hr", inline=True
                )
                embed.add_field(
                    name="Miss Distance:", value=f"{miss_dist} KM", inline=True
                )
                embed.add_field(name="Orbiting:", value=f"{orbiting}", inline=True)
                embed.add_field(
                    name="Is sentry?", value=f"{is_sentry_object}", inline=True
                )
                embed.set_thumbnail(
                    url="https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png"
                )
                embed.set_footer(text=f"Page {index+1}/{len(date)} | {ctx.author.name}")
        if not em_list:
            return await ctx.send(f"{ctx.author.mention} no results")
        await PaginationView(em_list).start(ctx=ctx)
        # paginator = Paginator(pages=em_list, timeout=60.0)

        # await paginator.start(ctx)

    @commands.command(aliases=["findaid", "asteroidid"])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def findasteroididid(self, ctx: Context, id: int):
        """Find any asteroid in the space by ID. "$help findaid" for syntax"""
        link = f"https://api.nasa.gov/neo/rest/v1/neo/{id}?api_key={NASA_KEY}"

        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        name = res["name"]
        link_self = res["nasa_jpl_url"]

        dia = round(res["estimated_diameter"]["meters"]["estimated_diameter_min"])
        danger = res["is_potentially_hazardous_asteroid"]
        sentry = res["is_sentry_object"]
        orbitaldata = res["orbital_data"]["orbit_class"]["orbit_class_description"]
        orbital_ran = res["orbital_data"]["orbit_class"]["orbit_class_range"]
        last_obs = res["orbital_data"]["last_observation_date"]
        orbit_sp = res["close_approach_data"][0]["relative_velocity"][
            "kilometers_per_hour"
        ]
        orbital_p = res["close_approach_data"][0]["orbiting_body"]
        embed = discord.Embed(
            title=f"Asteroid Name: {name}",
            url=f"{link_self}",
            description=f"{orbitaldata}\nRange: {orbital_ran}",
        )
        embed.add_field(name="Estimated Diameter:", value=f"{dia} M", inline=True)
        embed.add_field(name="Is Danger?", value=f"{danger}", inline=True)
        embed.add_field(name="Is sentry?", value=f"{sentry}", inline=True)
        embed.add_field(
            name="Relative velocity:", value=f"{orbit_sp} KM/hr", inline=True
        )
        embed.add_field(name="Orbiting:", value=f"{orbital_p}", inline=True)
        embed.add_field(name="Last observation date:", value=f"{last_obs}", inline=True)
        embed.set_thumbnail(
            url="https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png"
        )
        embed.set_footer(text=f"{ctx.author.name}")

        await ctx.reply(embed=embed)

    @commands.command(aliases=["mrp"])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def mars(self, ctx: Context, date: str):
        """Mars Rovers Pictures. Date must be in "YYYY-MM-DD" format"""
        link = f"https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/photos?earth_date={date}&api_key={NASA_KEY}"

        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        em_list = []

        for index in range(0, len(res["photos"])):
            img = res["photos"][index]["img_src"]
            date_ = res["photos"][index]["earth_date"]
            status = res["photos"][index]["rover"]["status"].capitalize()

            embed = discord.Embed(
                title="Mars Rover Photos",
                description=f"Status: {status} | Date of imagery: {date_}",
                timestamp=datetime.utcnow(),
            )
            embed.set_image(url=f"{img}")
            embed.set_footer(
                text=f"Page {index+1}/{len(res['photos'])} | {ctx.author.name}"
            )
            embed.set_thumbnail(
                url="https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png"
            )
            em_list.append(embed)
        if not em_list:
            return await ctx.send(f"{ctx.author.mention} no results")
        await PaginationView(em_list).start(ctx=ctx)
        # paginator = Paginator(pages=em_list, timeout=60.0)

        # await paginator.start(ctx)

    @commands.command(aliases=["nsearch", "ns"])
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def nasasearch(self, ctx: Context, *, string: commands.clean_content):
        """NASA Image and Video Library"""
        link = f"https://images-api.nasa.gov/search?q={string}"
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as r:
                if r.status >= 300:
                    return await ctx.reply(
                        f"{ctx.author.mention} could not find **{string}** in NASA Image and Video Library | Http status: {r.status}"
                    )
                res = await r.json()

        if not res["collection"]["items"]:
            await ctx.reply(
                f"{ctx.author.mention} could not find **{string}** in NASA Image and Video Library."
            )
        em_list = []
        for index in range(0, len(res["collection"]["items"])):
            title = res["collection"]["items"][index]["data"][0]["title"]
            description = res["collection"]["items"][index]["data"][0]["description"]
            preview = res["collection"]["items"][index]["links"][0]["href"]

            async with aiohttp.ClientSession() as session:
                async with session.get() as r:
                    if r.status == 200:
                        media = r.json()
                    else:
                        pass
            img, vid, srt = [], [], []
            i, j, k = 1, 1, 1
            for link in media:
                if link.endswith(".jpg") or link.endswith(".png"):
                    img.append(f"[Link {i}]({link})")
                    i += 1
                if link.endswith(".mp4"):
                    vid.append(f"[Link {j}]({link})")
                    j += 1
                if link.endswith(".str"):
                    srt.append(f"[Link {k}]({link})")
                    k += 1

            embed = discord.Embed(
                title=f"{title}",
                description=f"{description}",
                timestamp=datetime.utcnow(),
            )
            embed.set_image(url=f"{preview}")
            if img:
                embed.add_field(name="Images", value=f"{', '.join(img)}", inline=False)
            if vid:
                embed.add_field(name="Videos", value=f"{', '.join(vid)}", inline=False)
            if srt:
                embed.add_field(name="Srt", value=f"{', '.join(srt)}", inline=False)
            embed.set_footer(
                f"Page {index+1}/{len(res['collection']['items'])} | {ctx.author.name}"
            )
            embed.set_thumbnail(
                url="https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png"
            )
            em_list.append(embed)
        if not em_list:
            return await ctx.send(f"{ctx.author.mention} no results")
        await PaginationView(em_list).start(ctx=ctx)
        # paginator = Paginator(pages=em_list, timeout=60.0)
        # await paginator.start(ctx)
