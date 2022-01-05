from __future__ import annotations

from core import Parrot, Context, Cog
import discord
from discord.ext import commands
import aiohttp
from datetime import datetime


class Actions(Cog):
    """Action commands like hug and kiss"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.url = "https://api.waifu.pics/sfw"

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(
            name="Lights_Camera_Action__Emoticon__", id=892434144364220497
        )

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def waifu(self, ctx: Context, *, member: discord.Member = None):
        """Waifu pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def shinobu(self, ctx: Context, *, member: discord.Member = None):
        """Shinobu pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def megumin(self, ctx: Context, *, member: discord.Member = None):
        """Megumin pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def bully(self, ctx: Context, *, member: discord.Member = None):
        """Bully pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def cuddle(self, ctx: Context, *, member: discord.Member = None):
        """Cuddle pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def weep(self, ctx: Context, *, member: discord.Member = None):
        """Cry pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def hug(self, ctx: Context, *, member: discord.Member = None):
        """Hug pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(
            title=f"{ctx.author} hugged {member if member else ''}",
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
        )
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def awoo(self, ctx: Context, *, member: discord.Member = None):
        """Awoo pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def kiss(self, ctx: Context, *, member: discord.Member = None):
        """Kiss pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(
            title=f"{ctx.author} kisses {member if member else ''}",
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
        )
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def lick(self, ctx: Context, *, member: discord.Member = None):
        """Lick pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(
            title=f"{ctx.author} licks {member if member else ''}",
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
        )
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def pat(self, ctx: Context, *, member: discord.Member = None):
        """Pat pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(
            title=f"{ctx.author} pats {member if member else ''}",
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
        )
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def smug(self, ctx: Context, *, member: discord.Member = None):
        """Smug pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def bonk(self, ctx: Context, *, member: discord.Member = None):
        """Bonk pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def yeet(self, ctx: Context, *, member: discord.Member = None):
        """Yeet pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def blush(self, ctx: Context, *, member: discord.Member = None):
        """Blush pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def smile(self, ctx: Context, *, member: discord.Member = None):
        """Smile pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def wave(self, ctx: Context, *, member: discord.Member = None):
        """Wave pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(
            title=f"{ctx.author} waves {member if member else ''}",
            color=ctx.author.color,
            timestamp=datetime.utcnow(),
        )
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def highfive(self, ctx: Context, *, member: discord.Member = None):
        """Highfive pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def handhold(self, ctx: Context, *, member: discord.Member = None):
        """Handhold pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def nom(self, ctx: Context, *, member: discord.Member = None):
        """Nom pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def bite(self, ctx: Context, *, member: discord.Member = None):
        """Bite pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def glomp(self, ctx: Context, *, member: discord.Member = None):
        """Glomp pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def slap(
        self,
        ctx: Context,
        member: discord.Member,
        *,
        reason: commands.clean_content = None,
    ):
        """Slap pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(
            content=f"{ctx.author.mention} slapped {member.name} for {reason if reason else 'No reason'}",
            embed=em,
        )

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def kill(self, ctx: Context, *, member: discord.Member = None):
        """Kill pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def hit(self, ctx: Context, *, member: discord.Member = None):
        """Kick pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/kick")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def happy(self, ctx: Context, *, member: discord.Member = None):
        """Happy pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def wink(self, ctx: Context, *, member: discord.Member = None):
        """Wink pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def poke(self, ctx: Context, *, member: discord.Member = None):
        """Poke pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def dance(self, ctx: Context, *, member: discord.Member = None):
        """Dance pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def cringe(self, ctx: Context, *, member: discord.Member = None):
        """Cringe pics?"""
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"{self.url}/{ctx.command.name}")

        json = await data.json()
        url = json["url"]
        em = discord.Embed(color=ctx.author.color, timestamp=datetime.utcnow())
        em.set_image(url=url)
        em.set_footer(text=f"{ctx.author}")

        await ctx.reply(embed=em)
