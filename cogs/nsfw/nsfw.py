from __future__ import annotations

import time
from typing import Dict, List, Literal, Optional, Set
from random import random, choice
import discord
from core import Cog, Context, Parrot
from discord.ext import commands
from utilities.paginator import PaginationView as PV

from ._nsfw import ENDPOINTS


class NSFW(Cog):
    """Want some fun? These are best commands! :') :warning: 18+"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.url = "https://nekobot.xyz/api/image"
        self.command_loader()

        self.cached_images: Dict[str, Set[str]] = {}

        self.ON_TESTING = False

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{NO ONE UNDER EIGHTEEN SYMBOL}")

    async def cog_check(self, ctx: Context) -> Optional[bool]:
        if not ctx.channel.nsfw:
            raise commands.NSFWChannelRequired(ctx.channel)
        return True

    def _try_from_cache(self, type_str: str) -> Optional[str]:
        return choice(self.cached_images.get(type_str, [None]))

    async def get_embed(self, type_str: str) -> Optional[discord.Embed]:
        if random() > 0.5 and len(self.cached_images.get(type_str, [])) >= 10:
            url = choice(self.cached_images[type_str])
        else:
            response = await self.bot.http_session.get(
                self.url, params={"type": type_str}
            )
            if response.status > 300:
                url = self._try_from_cache(type_str)
                if url is None:
                    return None
            else:
                url = (await response.json())["message"]
        embed = discord.Embed(
            title=f"{type_str.title()}",
            color=self.bot.color,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_image(url=url)

        if type_str not in self.cached_images:
            self.cached_images[type_str] = set()
        self.cached_images[type_str].add(url)
        return embed

    def command_loader(self) -> None:
        for end_point in ENDPOINTS:

            @commands.command(name=end_point)
            @commands.is_nsfw()
            @Context.with_type
            async def callback(ctx: Context):
                embed = await self.get_embed(f"{ctx.command.qualified_name}")
                if embed is not None:
                    await ctx.reply(
                        embed=embed.set_footer(
                            text=f"Requested by {ctx.author}",
                            icon_url=ctx.author.display_avatar.url,
                        )
                    )
                else:
                    await ctx.reply(
                        f"{ctx.author.mention} something not right? This is not us but the API"
                    )

            self.bot.add_command(callback)

    @commands.command(aliases=["randnsfw"], hidden=True)
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
    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def n(
        self,
        ctx: Context,
        count: Optional[int] = 1,
        *,
        endpoint: Literal["gif", "jav", "rb", "ahegao", "twitter"] = "gif",
    ) -> None:
        """Best command I guess. It return random ^^"""
        em_list: List[discord.Embed] = []

        if count is not None and count <= 0:
            return await ctx.reply(f"{ctx.author.mention} count must be greater than 0")

        i: int = 1
        while i <= count:
            r = await self.bot.http_session.get(
                f"https://scathach.redsplit.org/v3/nsfw/{endpoint}/",
                headers=self.bot.GLOBAL_HEADERS,
            )
            if r.status == 200:
                res = await r.json()
                em_list.append(
                    discord.Embed(timestamp=discord.utils.utcnow()).set_image(
                        url=res["url"]
                    )
                )
            await ctx.release(0)
            i += 1

        ins = PV(em_list)
        ins.message = await ins.paginate(ctx)
