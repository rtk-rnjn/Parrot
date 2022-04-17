from __future__ import annotations

import discord
import datetime
import time
from discord.ext import commands

from core import Parrot, Context, Cog


class NSFW(Cog):
    """Want some fun? These are best commands! :') :warning: 18+"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.url = "https://nekobot.xyz/api/image"

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{NO ONE UNDER EIGHTEEN SYMBOL}")

    async def get_embed(self, type_str: str) -> discord.Embed:
        response = await self.bot.http_session.get(self.url, params={"type": type_str})
        if response.status != 200:
            return
        url = (await response.json())["message"]
        embed = discord.Embed(title=f"{type_str.title()}", color=self.bot.color, timestamp=datetime.datetime.utcnow())
        embed.set_image(url=url)
        return embed

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def anal(self, ctx: Context):
        """To get Random Anal"""
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def gonewild(self, ctx: Context):
        """
        To get Random GoneWild
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def hanal(self, ctx: Context):
        """To get Random Hentai Anal"""
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def hentai(self, ctx: Context):
        """To get Random Hentai"""
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def holo(self, ctx: Context):
        """
        To get Random Holo
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def neko(self, ctx: Context):
        """
        To get Random Neko
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def hneko(self, ctx: Context):
        """
        To get Random Hneko
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def hkitsune(self, ctx: Context):
        """
        To get Random Hkitsune
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def kemonomimi(self, ctx: Context):
        """
        To get Random Kemonomimi
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def pgif(self, ctx: Context):
        """
        To get Random PornGif
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command(name="4k")
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def _4k(self, ctx: Context):
        """
        To get Random 4k
        """
        await ctx.reply(embed=await self.get_embed("4k"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def kanna(self, ctx: Context):
        """
        To get Random Kanna
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def ass(self, ctx: Context):
        """
        To get Random Ass
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def pussy(self, ctx: Context):
        """
        To get Random Pussy
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def thigh(self, ctx: Context):
        """
        To get Random Thigh
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def hthigh(self, ctx: Context):
        """
        To get Random Hentai Thigh
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def paizuri(self, ctx: Context):
        """
        To get Random Paizuri
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def tentacle(self, ctx: Context):
        """
        To get Random Tentacle Porn
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def boobs(self, ctx: Context):
        """
        To get Random Boobs
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def hboobs(self, ctx: Context):
        """
        To get Random Hentai Boobs
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def yaoi(self, ctx: Context):
        """
        To get Random Yaoi
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def hmidriff(self, ctx: Context):
        """
        To get Random Hmidriff
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def hass(self, ctx: Context):
        """
        To get Random Hentai Ass
        """
        await ctx.reply(embed=await self.get_embed(f"{ctx.command.name}"))

    @commands.command(aliases=["randnsfw"])
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def randomnsfw(self, ctx: Context, *, subreddit: str = None):
        """
        To get Random NSFW from subreddit.
        """
        if subreddit is None:
            subreddit = "NSFW"
        end = time.time() + 60
        while time.time() < end:
            url = f"https://memes.blademaker.tv/api/{subreddit}"
            r = await self.bot.http_session.get(url)
            if r.status == 200:
                res = await r.json()
            else:
                return
            if res["nsfw"]:
                break

        img = res["image"]

        em = discord.Embed(timestamp=datetime.datetime.utcnow())
        em.set_footer(text=f"{ctx.author.name}")
        em.set_image(url=img)

        await ctx.reply(embed=em)

    @commands.command()
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def n(self, ctx: Context):
        """
        Best command I guess. It return random ^^
        """
        r = await self.bot.http_session.get("https://scathach.redsplit.org/v3/nsfw/gif/")
        if r.status == 200:
            res = await r.json()
        else:
            return

        img = res["url"]

        em = discord.Embed(timestamp=datetime.datetime.utcnow())
        em.set_footer(text=f"{ctx.author.name}")
        em.set_image(url=img)

        await ctx.reply(embed=em)
