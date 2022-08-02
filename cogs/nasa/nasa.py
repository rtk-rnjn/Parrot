from __future__ import annotations

import io
import os
import random
from datetime import datetime
from typing import Optional

import discord
from core import Cog, Context, Parrot
from discord.ext import commands
from utilities.paginator import PaginationView

NASA_KEY = os.environ["NASA_KEY"]

with open(r"extra/user_agents.txt") as f:
    USER_AGENTS = f.read().splitlines()


def date_parser(arg: Optional[str] = None) -> str:
    """Validate whether the given string is in YYYY-MM-DD format."""
    if arg is None:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        datetime.strptime(arg, "%Y-%m-%d")
    except ValueError:
        raise commands.BadArgument("Invalid date format. Use YYYY-MM-DD") from None
    return arg


def upper_split(ini_str: str) -> str:
    """To split the the given string by camel case"""
    res_pos = [i for i, e in enumerate(f"{ini_str}A") if e.isupper()]
    res_list = [ini_str[res_pos[j] : res_pos[j + 1]] for j in range(len(res_pos) - 1)]
    return " ".join(res_list)


class NASA(Cog):
    """Incredible NASA API Integration"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.random_agent = random.choice

        self._cache: dict = {}

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="nasa", id=892425662864982056)

    @commands.command(aliases=["sat", "satelite"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def earth(
        self, ctx: Context, longitute: float, latitude: float, date: date_parser
    ):
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
            title="Earth",
            colour=discord.Colour.blue(),
            timestamp=discord.utils.utcnow(),
        )
        res = await self.bot.http_session.get(link)
        file = discord.File(io.BytesIO(await res.read()), filename="earth.jpg")
        embed.set_image(
            url="attachment://earth.jpg",
        )
        embed.set_thumbnail(
            url="https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png"
        )
        embed.set_footer(text=f"{ctx.author.name}")

        await ctx.reply(embed=embed, file=file)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def apod(self, ctx: Context):
        """Asteroid Picture of the Day"""
        link = f"https://api.nasa.gov/planetary/apod?api_key={NASA_KEY}"

        r = await self.bot.http_session.get(link)
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
            timestamp=discord.utils.utcnow(),
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
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def epic(self, ctx: Context, date: date_parser):
        """Earth Polychromatic Imaging Camera. Date must be in "YYYY-MM-DD" format"""
        s_link = f"https://epic.gsfc.nasa.gov/api/images.php?date={date}"

        r = await self.bot.http_session.get(s_link)
        if r.status == 200:
            res = await r.json()
        else:
            return

        em_list = []
        for index in range(len(res)):
            caption = res[index]["caption"]
            im = res[index]["image"]
            lat = res[index]["centroid_coordinates"]["lat"]
            lon = res[index]["centroid_coordinates"]["lon"]
            link = f"https://epic.gsfc.nasa.gov/epic-archive/jpg/{im}.jpg"
            embed = discord.Embed(
                title=f"{caption}",
                colour=discord.Colour.blue(),
                description=f"Lat: {lat} | Lon: {lon}",
                timestamp=discord.utils.utcnow(),
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

    @commands.command(aliases=["finda", "asteroid", "neo"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def findasteroid(self, ctx: Context, start: date_parser, end: date_parser):
        """You can literally find any asteroid in the space by date. Date must be in "YYYY-MM-DD" format"""
        link = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={start}&end_date={end}&api_key={NASA_KEY}"

        r = await self.bot.http_session.get(link)
        if r.status == 200:
            res = await r.json()
        else:
            return
        em_list = []

        for date in res["near_earth_objects"]:
            for index in range(len(res["near_earth_objects"][date])):
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
                    timestamp=discord.utils.utcnow(),
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

    @commands.command(aliases=["findaid", "asteroidid"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def findasteroididid(self, ctx: Context, asteroid_id: int):
        """Find any asteroid in the space by ID. "$help findaid" for syntax"""
        link = f"https://api.nasa.gov/neo/rest/v1/neo/{asteroid_id}?api_key={NASA_KEY}"

        r = await self.bot.http_session.get(link)
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
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def mars(self, ctx: Context, date: date_parser):
        """Mars Rovers Pictures. Date must be in "YYYY-MM-DD" format"""
        link = f"https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/photos?earth_date={date}&api_key={NASA_KEY}"

        r = await self.bot.http_session.get(link)
        if r.status == 200:
            res = await r.json()
        else:
            return

        em_list = []

        for index in range(len(res["photos"])):
            img = res["photos"][index]["img_src"]
            date_ = res["photos"][index]["earth_date"]
            status = res["photos"][index]["rover"]["status"].capitalize()

            embed = discord.Embed(
                title="Mars Rover Photos",
                description=f"Status: {status} | Date of imagery: {date_}",
                timestamp=discord.utils.utcnow(),
            )
            embed.set_image(url=f"{img}")
            embed.set_footer(text=f"Requested by {ctx.author}")
            embed.set_thumbnail(
                url="https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png"
            )
            em_list.append(embed)
        if not em_list:
            return await ctx.send(f"{ctx.author.mention} no results")
        await PaginationView(em_list).start(ctx=ctx)

    @commands.command(aliases=["nsearch", "ns"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def nasasearch(
        self, ctx: Context, limit: Optional[int] = 10, *, string: commands.clean_content
    ):
        """NASA Image and Video Library"""
        link = f"https://images-api.nasa.gov/search?q={string}"
        AGENT = self.random_agent(USER_AGENTS)
        r = await self.bot.http_session.get(link, headers={"User-Agent": AGENT})
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
        for index in range(len(res["collection"]["items"])):
            if data := res["collection"]["items"][index]:
                try:
                    title = data["data"][0]["title"]
                    description = data["data"][0]["description"]
                    preview = data["links"][0]["href"].replace(" ", "%20")
                    media_url = data["href"]
                    render = data["links"][0]["render"]
                except KeyError:
                    continue
                else:
                    r = await self.bot.http_session.get(
                        media_url, headers={"User-Agent": AGENT}
                    )
                    media = await r.json() if r.status == 200 else None
                    img, vid, srt = [], [], []
                    if media:
                        i, j, k = 1, 1, 1
                        for link in media[:10]:
                            if link.endswith(".jpg") or link.endswith(".png"):
                                img.append(f"[Image {i}]({link.replace(' ', '%20')})")
                                i += 1
                            if link.endswith(".mp4"):
                                vid.append(f"[Video {j}]({link.replace(' ', '%20')})")
                                j += 1
                            if link.endswith(".str"):
                                srt.append(f"[Link {k}]({link.replace(' ', '%20')})")
                                k += 1

                    embed = discord.Embed(
                        title=f"{title}",
                        description=f"{description[:1000]}...",
                        timestamp=discord.utils.utcnow(),
                    )
                    if render == "image":
                        embed.set_image(url=f"{preview}")
                    if img:
                        embed.add_field(
                            name="Images", value=f"{', '.join(img[:5])}", inline=False
                        )
                    if vid:
                        embed.add_field(
                            name="Videos", value=f"{', '.join(vid[:5])}", inline=False
                        )
                    if srt:
                        embed.add_field(
                            name="Srt", value=f"{', '.join(srt)}", inline=False
                        )
                    embed.set_footer(text=f"Requested by {ctx.author}")
                    embed.set_thumbnail(
                        url="https://assets.stickpng.com/images/58429400a6515b1e0ad75acc.png"
                    )
                    em_list.append(embed)
            if index >= limit:
                break
        if not em_list:
            return await ctx.send(f"{ctx.author.mention} no results")
        await PaginationView(em_list).start(ctx=ctx)

    @commands.group()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def donki(
        self,
        ctx: Context,
    ):
        """Space Weather Database Of Notifications, Knowledge, Information (DONKI)"""
        if not ctx.invoked_subcommand:
            await self.bot.invoke_help_command(ctx)

    @donki.command(name="cme")
    async def donki_cme(self, ctx: Context, start: date_parser, end: date_parser):
        """Coronal Mass Ejection"""
        url = f"https://api.nasa.gov/DONKI/CME?startDate={start}&endDate={end}&api_key={NASA_KEY}"
        AGENT = self.random_agent(USER_AGENTS)
        r = await self.bot.http_session.get(url, headers={"User-Agent": AGENT})
        if r.status >= 300:
            return await ctx.reply(
                f"{ctx.author.mention} could not find CME in DONKI | Http status: {r.status}"
            )
        res = await r.json()
        if not res:
            return await ctx.reply(f"{ctx.author.mention} no results")

        em_list = []

        for data in res:
            em = discord.Embed()

            activity_id = data["activityID"]
            catalog = data["catalog"]
            start_time = data["startTime"]
            source_location = data["sourceLocation"]
            active_region_num = data["activeRegionNum"]
            link = data["link"]
            note = data["note"]
            instruments = ", ".join(
                i["displayName"] for i in data.get("instruments", [])
            )

            em.description = f"""
Activity ID: {activity_id}
Catalog: {catalog}
Start Time: {start_time}
Source Location: {source_location}
Active Region Num: {active_region_num}
Link: {link}
Instuments: {instruments}
"""
            em.title = catalog
            em.url = link

            em_list.append(em)
        await PaginationView(em_list).start(ctx=ctx)

    @donki.command(name="gst")
    async def donki_gst(self, ctx: Context, start: date_parser, end: date_parser):
        """Geomagnetic Storm"""
        link = f"https://api.nasa.gov/DONKI/GST?startDate={start}&endDate={end}&api_key={NASA_KEY}"
        AGENT = self.random_agent(USER_AGENTS)
        r = await self.bot.http_session.get(link, headers={"User-Agent": AGENT})
        if r.status >= 300:
            return await ctx.reply(
                f"{ctx.author.mention} could not find GST in DONKI | Http status: {r.status}"
            )
        res = await r.json()
        if not res:
            return await ctx.reply(f"{ctx.author.mention} no results")

        em_list = []

        for data in res:
            em = discord.Embed()
            gstID = data["gstID"]
            startTime = data["startTime"]
            link = data["link"]

            em.description = f"""
GST ID: {gstID}
Start Time: {startTime}
Link: {link}
"""
            em_list.append(em)
        await PaginationView(em_list).start(ctx=ctx)

    @donki.command(name="ips")
    async def donki_ips(self, ctx: Context, start: date_parser, end: date_parser):
        """Interplanetary Shock"""
        link = f"https://api.nasa.gov/DONKI/IPS?startDate={start}&endDate={end}&api_key={NASA_KEY}"
        AGENT = self.random_agent(USER_AGENTS)
        r = await self.bot.http_session.get(link, headers={"User-Agent": AGENT})
        if r.status >= 300:
            return await ctx.reply(
                f"{ctx.author.mention} could not find IPS in DONKI | Http status: {r.status}"
            )
        res = await r.json()
        if not res:
            return await ctx.reply(f"{ctx.author.mention} no results")

        em_list = []

        for data in res:
            em = discord.Embed()
            catalog = data["catalog"]
            activityID = data["activityID"]
            location = data["location"]
            eventTime = data["eventTime"]
            link = data["link"]
            instruments = ", ".join(
                i["displayName"] for i in data.get("instruments", [])
            )
            em.description = f"""
Catalog: {catalog}
Activity ID: {activityID}
Location: {location}
Event Time: {eventTime}
Link: {link}
Instuments: {instruments}
"""
            em.title = catalog
            em.url = link

            em_list.append(em)
        await PaginationView(em_list).start(ctx=ctx)

    @donki.command(name="flr")
    async def donki_flr(self, ctx: Context, start: date_parser, end: date_parser):
        """Solar Flare"""
        link = f"https://api.nasa.gov/DONKI/FLR?startDate={start}&endDate={end}&api_key={NASA_KEY}"
        AGENT = self.random_agent(USER_AGENTS)
        r = await self.bot.http_session.get(link, headers={"User-Agent": AGENT})
        if r.status >= 300:
            return await ctx.reply(
                f"{ctx.author.mention} could not find FLR in DONKI | Http status: {r.status}"
            )
        res = await r.json()
        if not res:
            return await ctx.reply(f"{ctx.author.mention} no results")

        em_list = []

        for data in res:
            em = discord.Embed()
            flrID = data["flrID"]
            instruments = ", ".join(
                i["displayName"] for i in data.get("instruments", [])
            )
            beginTime = data["beginTime"]
            peakTime = data["peakTime"]
            endTime = data["endTime"]
            classType = data["classType"]
            sourceLocation = data["sourceLocation"]
            activeRegionNum = data["activeRegionNum"]
            linkedEvents = ", ".join(
                i["activityID"] for i in data.get("linkedEvents", [])
            )
            link = data["link"]
            em.description = f"""
FLR ID: {flrID}
Instruments: {instruments}
Begin Time: {beginTime}
Peak Time: {peakTime}
End Time: {endTime}
Class Type: {classType}
Source Location: {sourceLocation}
Active Region Num: {activeRegionNum}
Linked Events: {linkedEvents}
Link: {link}
"""
            em.title = flrID
            em.url = link

            em_list.append(em)
        await PaginationView(em_list).start(ctx=ctx)

    @donki.command(name="sep")
    async def donki_sep(self, ctx: Context, start: date_parser, end: date_parser):
        """Solar Energetic Particle"""
        link = f"https://api.nasa.gov/DONKI/SEP?startDate={start}&endDate={end}&api_key={NASA_KEY}"
        AGENT = self.random_agent(USER_AGENTS)
        r = await self.bot.http_session.get(link, headers={"User-Agent": AGENT})
        if r.status >= 300:
            return await ctx.reply(
                f"{ctx.author.mention} could not find SEP in DONKI | Http status: {r.status}"
            )
        res = await r.json()
        if not res:
            return await ctx.reply(f"{ctx.author.mention} no results")

        em_list = []

        for data in res:
            em = discord.Embed()
            sepID = data["sepID"]
            instruments = ", ".join(
                i["displayName"] for i in data.get("instruments", [])
            )
            eventTime = data["eventTime"]

            linkedEvents = ", ".join(
                i["activityID"] for i in data.get("linkedEvents", [])
            )
            link = data["link"]
            em.description = f"""
SEP ID: {sepID}
Instruments: {instruments}
Event Time: {eventTime}
Linked Events: {linkedEvents}
Link: {link}
"""
            em.title = sepID
            em.url = link

            em_list.append(em)
        await PaginationView(em_list).start(ctx=ctx)

    @donki.command(name="mpc")
    async def donki_mpc(self, ctx: Context, start: date_parser, end: date_parser):
        """Magnetopause Crossing"""
        link = f"https://api.nasa.gov/DONKI/MPC?startDate={start}&endDate={end}&api_key={NASA_KEY}"
        AGENT = self.random_agent(USER_AGENTS)
        r = await self.bot.http_session.get(link, headers={"User-Agent": AGENT})
        if r.status >= 300:
            return await ctx.reply(
                f"{ctx.author.mention} could not find MPC in DONKI | Http status: {r.status}"
            )
        res = await r.json()
        if not res:
            return await ctx.reply(f"{ctx.author.mention} no results")

        em_list = []

        for data in res:
            em = discord.Embed()
            mpcID = data["mpcID"]
            eventTime = data["eventTime"]
            instruments = ", ".join(
                i["displayName"] for i in data.get("instruments", [])
            )
            link = data["link"]
            em.description = f"""
MPC ID: {mpcID}
Event Time: {eventTime}
Link: {link}
Instuments: {instruments}
"""
            em.title = mpcID
            em.url = link

            em_list.append(em)
        await PaginationView(em_list).start(ctx=ctx)

    @donki.command(name="rbe")
    async def donki_rbe(self, ctx: Context, start: date_parser, end: date_parser):
        """Radiation Belt Enhancement"""
        link = f"https://api.nasa.gov/DONKI/RBE?startDate={start}&endDate={end}&api_key={NASA_KEY}"
        AGENT = self.random_agent(USER_AGENTS)
        r = await self.bot.http_session.get(link, headers={"User-Agent": AGENT})
        if r.status >= 300:
            return await ctx.reply(
                f"{ctx.author.mention} could not find RBE in DONKI | Http status: {r.status}"
            )
        res = await r.json()
        if not res:
            return await ctx.reply(f"{ctx.author.mention} no results")

        em_list = []

        for data in res:
            em = discord.Embed()
            rbeID = data["rbeID"]
            eventTime = data["eventTime"]
            instruments = ", ".join(
                i["displayName"] for i in data.get("instruments", [])
            )
            link = data["link"]
            em.description = f"""
RBE ID: {rbeID}
Event Time: {eventTime}
Link: {link}
Instuments: {instruments}
"""
            em.title = rbeID
            em.url = link

            em_list.append(em)
        await PaginationView(em_list).start(ctx=ctx)

    @donki.command(name="hhs")
    async def donki_hhs(self, ctx: Context, start: date_parser, end: date_parser):
        """Hight Speed Stream"""
        link = f"https://api.nasa.gov/DONKI/HHS?startDate={start}&endDate={end}&api_key={NASA_KEY}"
        AGENT = self.random_agent(USER_AGENTS)
        r = await self.bot.http_session.get(link, headers={"User-Agent": AGENT})
        if r.status >= 300:
            return await ctx.reply(
                f"{ctx.author.mention} could not find HHS in DONKI | Http status: {r.status}"
            )
        res = await r.json()
        if not res:
            return await ctx.reply(f"{ctx.author.mention} no results")

        em_list = []

        for data in res:
            em = discord.Embed()
            hhsID = data["hhsID"]
            eventTime = data["eventTime"]
            instruments = ", ".join(
                i["displayName"] for i in data.get("instruments", [])
            )
            link = data["link"]
            em.description = f"""
HHS ID: {hhsID}
Event Time: {eventTime}
Link: {link}
Instuments: {instruments}
"""
            em.title = hhsID
            em.url = link

            em_list.append(em)
        await PaginationView(em_list).start(ctx=ctx)
