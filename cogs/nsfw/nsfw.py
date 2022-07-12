from __future__ import annotations

import time
from typing import Optional

import discord
from core import Cog, Context, Parrot
from discord.ext import commands

from ._nsfw import ENDPOINTS


class NSFW(Cog):
    """Want some fun? These are best commands! :') :warning: 18+"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.url = "https://nekobot.xyz/api/image"
        self.command_loader()

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{NO ONE UNDER EIGHTEEN SYMBOL}")

    async def get_embed(self, type_str: str) -> Optional[discord.Embed]:
        response = await self.bot.http_session.get(self.url, params={"type": type_str})
        if response.status != 200:
            return None
        url = (await response.json())["message"]
        embed = discord.Embed(
            title=f"{type_str.title()}",
            color=self.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_image(url=url)
        return embed

    def command_loader(self) -> None:
        for end_point in ENDPOINTS:

            @commands.command(name=end_point)
            @commands.is_nsfw()
            @commands.bot_has_permissions(embed_links=True)
            @Context.with_type
            async def callback(ctx: Context):
                embed = await self.get_embed(f"{ctx.command.name}")
                if embed is not None:
                    await ctx.reply(embed=embed)
                else:
                    await ctx.reply("{ctx.author.mention} something not right? This is not use but the API")

            self.bot.add_command(callback)

    @commands.command(aliases=["randnsfw"], hidden=True)
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def randomnsfw(self, ctx: Context, *, subreddit: str = None) -> None:
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

        em = discord.Embed(timestamp=discord.utils.utcnow())
        em.set_footer(text=f"{ctx.author.name}")
        em.set_image(url=img)

        await ctx.reply(embed=em)

    @commands.command(hidden=True)
    @commands.is_nsfw()
    @commands.bot_has_permissions(embed_links=True)
    @Context.with_type
    async def n(self, ctx: Context) -> None:
        """
        Best command I guess. It return random ^^
        """
        r = await self.bot.http_session.get(
            "https://scathach.redsplit.org/v3/nsfw/gif/"
        )
        if r.status == 200:
            res = await r.json()
        else:
            return

        img = res["url"]

        em = discord.Embed(timestamp=discord.utils.utcnow())
        em.set_footer(text=f"{ctx.author.name}")
        em.set_image(url=img)

        await ctx.reply(embed=em)
