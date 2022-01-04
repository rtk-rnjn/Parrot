from __future__ import annotations

import discord
import aiohttp
from discord.ext import commands

from datetime import datetime
from core import Parrot, Context, Cog

from utilities.config import MEME_PASS as meme_pass


class Memegen(Cog):
    """Be a memer, make memes using Parrot."""

    def __init__(self, bot: Parrot):
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{FACE WITH TEARS OF JOY}")

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def thefact(self, ctx: Context, *, text: str = None):
        """Meme Generator/Image Generator: The Fact"""
        params = {
            "type": "fact",
            "text": f"{text}",
        }
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def stickbug(self, ctx: Context, *, member: discord.Member = None):
        """Meme Generator/Image Generator: Stickbug"""
        if member is None:
            member = ctx.author
        params = {
            "type": "stickbug",
            "url": f"{member.display_avatar.url}",
        }
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def trash(self, ctx: Context, *, member: discord.Member = None):
        """
        Meme Generator/Image Generator: Trash
        """
        if member is None:
            member = ctx.author
        params = {
            "type": "trash",
            "url": f"{member.display_avatar.url}",
        }
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def magik(
        self, ctx: Context, member: discord.Member = None, intensity: int = None
    ):
        """
        Meme Generator/Image Generator: Magik
        """
        if member is None:
            member = ctx.author
        if intensity is None:
            intensity = 5
        params = {
            "type": "magik",
            "image": f"{member.display_avatar.url}",
            "intensity": intensity,
        }
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def blurpify(self, ctx: Context, *, member: discord.Member = None):
        """
        Meme Generator/Image Generator: Blurpify
        """
        if member is None:
            member = ctx.author
        params = {"type": "blurpify", "image": f"{member.display_avatar.url}"}
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def phcomment(self, ctx: Context, *, text: str = None):
        """
        Meme Generator/Image Generator: Porn Hub Comment
        """
        params = {
            "type": "phcomment",
            "image": f"{ctx.author.display_avatar.url}",
            "text": text,
            "username": f"{ctx.author.name}",
        }
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def deepfry(self, ctx: Context, *, member: discord.Member = None):
        """
        Meme Generator/Image Generator: Deep Fry
        """
        if member is None:
            member = ctx.author
        params = {"type": "deepfry", "image": f"{member.display_avatar.url}"}
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def tweet(self, ctx: Context, *, text: str = None):
        """
        Meme Generator/Image Generator: Tweet
        """
        if text is None:
            text = "No U"
        params = {"type": "tweet", "text": f"{text}", "username": f"{ctx.author.name}"}
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def trumptweet(self, ctx: Context, *, text: str = None):
        """
        Meme Generator/Image Generator: Trump Tweet
        """
        if text is None:
            text = "No U"
        params = {"type": "trumptweet", "text": f"{text}"}
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def trap(self, ctx: Context, *, member: discord.Member = None):
        """
        Meme Generator/Image Generator: Trap
        """
        if member is None:
            member = ctx.author
        params = {
            "type": "trap",
            "name": f"{member.name}",
            "author": f"{ctx.author.name}",
            "image": f"{member.display_avatar.url}",
        }
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def awooify(self, ctx: Context, *, member: discord.Member = None):
        """
        Meme Generator/Image Generator: Awooify
        """
        if member is None:
            member = ctx.author
        params = {"type": "awooify", "url": f"{member.display_avatar.url}"}
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def animeface(self, ctx: Context, *, member: discord.Member = None):
        """
        Meme Generator/Image Generator: Anime Face
        """
        if member is None:
            member = ctx.author
        params = {"type": "animeface", "image": f"{member.display_avatar.url}"}
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def iphonex(self, ctx: Context, *, member: discord.Member = None):
        """
        Meme Generator/Image Generator: IphoneX
        """
        if member is None:
            member = ctx.author
        params = {"type": "iphonex", "url": f"{member.display_avatar.url}"}
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def threats(self, ctx: Context, *, member: discord.Member = None):
        """
        Meme Generator/Image Generator: Threats
        """
        if member is None:
            member = ctx.author
        params = {"type": "threats", "url": f"{member.display_avatar.url}"}
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def clyde(self, ctx: Context, *, text: str):
        """
        Meme Generator/Image Generator: Clyde
        """
        params = {"type": "clyde", "text": f"{text}"}
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def captcha(self, ctx: Context, *, member: discord.Member = None):
        """
        Meme Generator/Image Generator: Captcha
        """
        if member is None:
            member = ctx.author
        params = {
            "type": "captcha",
            "url": f"{member.display_avatar.url}",
            "username": f"{member.name}",
        }
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def whowouldwin(self, ctx: Context, *, member: discord.Member):
        """
        Meme Generator/Image Generator: Who would win
        """
        params = {
            "type": "whowouldwin",
            "user1": f"{member.display_avatar.url}",
            "user2": f"{ctx.author.display_avatar.url}",
        }
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def baguette(self, ctx: Context, *, member: discord.Member = None):
        """
        Meme Generator/Image Generator: Baguette
        """
        if member is None:
            member = ctx.author
        params = {"type": "baguette", "url": f"{member.display_avatar.url}"}
        url = "https://nekobot.xyz/api/imagegen"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return
        img = res["message"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)
        #

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def awkwardseal(
        self,
        ctx: Context,
        text1: str,
        text2: str,
        font: str = None,
        fontsize: int = None,
    ):
        """
        Meme Generator: Awkward Seal.
        """
        params = {
            "template_id": 13757816,
            "username": "RitikRanjan",
            "password": f"{meme_pass}",
            "text0": text1,
            "text1": text2,
            "font": font,
            "max_font_size": fontsize,
        }
        url = "https://api.imgflip.com/caption_image"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        if not res["success"]:
            return

        img = res["data"]["url"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def changemymind(
        self,
        ctx: Context,
        text1: str,
        text2: str,
        font: str = None,
        fontsize: int = None,
    ):
        """
        Meme Generator: Change My Mind.
        """
        font = font or "impact"
        fontsize = fontsize or 50

        params = {
            "template_id": 129242436,
            "username": "RitikRanjan",
            "password": f"{meme_pass}",
            "text0": text1,
            "text1": text2,
            "font": font,
            "max_font_size": fontsize,
        }
        url = "https://api.imgflip.com/caption_image"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        if not res["success"]:
            return

        img = res["data"]["url"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def distractedbf(
        self,
        ctx: Context,
        text1: str,
        text2: str,
        font: str = None,
        fontsize: int = None,
    ):
        """
        Meme Generator: Distracted BF.
        """
        font = font or "impact"
        fontsize = fontsize or 50

        params = {
            "template_id": 112126428,
            "username": "RitikRanjan",
            "password": f"{meme_pass}",
            "text0": text1,
            "text1": text2,
            "font": font,
            "max_font_size": fontsize,
        }
        url = "https://api.imgflip.com/caption_image"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        if not res["success"]:
            return

        img = res["data"]["url"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def doge(
        self,
        ctx: Context,
        text1: str,
        text2: str,
        font: str = None,
        fontsize: int = None,
    ):
        """
        Meme Generator: Doge.
        """
        font = font or "impact"
        fontsize = fontsize or 50
        params = {
            "template_id": 8072285,
            "username": "RitikRanjan",
            "password": f"{meme_pass}",
            "text0": text1,
            "text1": text2,
            "font": font,
            "max_font_size": fontsize,
        }
        url = "https://api.imgflip.com/caption_image"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        if not res["success"]:
            return

        img = res["data"]["url"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def drakeyesno(
        self,
        ctx: Context,
        text1: str,
        text2: str,
        font: str = None,
        fontsize: int = None,
    ):
        """
        Meme Generator: Drake Yes No.
        """
        font = font or "impact"
        fontsize = fontsize or 50
        params = {
            "template_id": 181913649,
            "username": "RitikRanjan",
            "password": f"{meme_pass}",
            "text0": text1,
            "text1": text2,
            "font": font,
            "max_font_size": fontsize,
        }
        url = "https://api.imgflip.com/caption_image"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        if not res["success"]:
            return

        img = res["data"]["url"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def isthispigeon(
        self,
        ctx: Context,
        text1: str,
        text2: str,
        font: str = None,
        fontsize: int = None,
    ):
        """
        Meme Generator: Is This Pigeon.
        """
        font = font or "impact"
        fontsize = fontsize or 50
        params = {
            "template_id": 100777631,
            "username": "RitikRanjan",
            "password": f"{meme_pass}",
            "text0": text1,
            "text1": text2,
            "font": font,
            "max_font_size": fontsize,
        }
        url = "https://api.imgflip.com/caption_image"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        if not res["success"]:
            return

        img = res["data"]["url"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def twobuttons(
        self,
        ctx: Context,
        text1: str,
        text2: str,
        font: str = None,
        fontsize: int = None,
    ):
        """
        Meme Generator: Two Buttons.
        """
        font = font or "impact"
        fontsize = fontsize or 50

        params = {
            "template_id": 87743020,
            "username": "RitikRanjan",
            "password": f"{meme_pass}",
            "text0": text1,
            "text1": text2,
            "font": font,
            "max_font_size": fontsize,
        }
        url = "https://api.imgflip.com/caption_image"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        if not res["success"]:
            return

        img = res["data"]["url"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def unodraw25(
        self,
        ctx: Context,
        text1: str,
        text2: str,
        font: str = None,
        fontsize: int = None,
    ):
        """
        Meme Generator: UNO Draw 25.
        """
        font = font or "impact"
        fontsize = fontsize or 50
        params = {
            "template_id": 217743513,
            "username": "RitikRanjan",
            "password": f"{meme_pass}",
            "text0": text1,
            "text1": text2,
            "font": font,
            "max_font_size": fontsize,
        }
        url = "https://api.imgflip.com/caption_image"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        if not res["success"]:
            return

        img = res["data"]["url"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @Context.with_type
    async def mastermeme(
        self,
        ctx: Context,
        template: int,
        text1: str,
        text2: str,
        font: str = None,
        fontsize: int = None,
    ):
        """
        To create a meme as per your choice.

        NOTE: Default Font is Impact and default Fontsize is 50. You can find tons and tons of template at https://imgflip.com/popular_meme_ids or at https://imgflip.com/
        """
        font = font or "impact"
        fontsize = fontsize or 50
        params = {
            "template_id": template,
            "username": "RitikRanjan",
            "password": f"{meme_pass}",
            "text0": text1,
            "text1": text2,
            "font": font,
            "max_font_size": fontsize,
        }
        url = "https://api.imgflip.com/caption_image"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as r:
                if r.status == 200:
                    res = await r.json()
                else:
                    return

        if not res["success"]:
            return

        img = res["data"]["url"]
        em = discord.Embed(title="", timestamp=datetime.utcnow())
        em.set_image(url=img)
        em.set_footer(text=f"{ctx.author.name}")
        await ctx.reply(embed=em)
