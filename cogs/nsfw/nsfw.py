from __future__ import annotations

from random import choice, random
from typing import Literal

import discord
from core import Cog, Context, Parrot
from discord.ext import commands
from utilities.exceptions import ParrotCheckFailure
from utilities.paginator import PaginationView as PV

from ._nsfw import ENDPOINTS


class NSFW(Cog):
    """Mature Content. 18+ only."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.url = "https://nekobot.xyz/api/image"

        self.cached_images: dict[str, set[str]] = {}
        self.ON_TESTING = False

    async def cog_load(self):
        self.command_loader()

    async def cog_unload(self):
        for end_point in ENDPOINTS:
            self.bot.remove_command(end_point)

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{NO ONE UNDER EIGHTEEN SYMBOL}")

    async def cog_check(self, ctx: Context) -> bool | None:
        if not ctx.channel.nsfw:
            raise commands.NSFWChannelRequired(ctx.channel)
        return True

    def _try_from_cache(self, type_str: str) -> str | None:
        return choice(self.cached_images.get(type_str, [None]))

    async def get_embed(self, type_str: str) -> discord.Embed:
        if random() > 0.5 and len(self.cached_images.get(type_str, [])) >= 10:
            url = choice(self.cached_images[type_str])
        else:
            response = await self.bot.http_session.get(self.url, params={"type": type_str})
            if response.status > 300:
                url = self._try_from_cache(type_str)
                if url is None:
                    msg = "Something went wrong with the API"
                    raise ParrotCheckFailure(msg)
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

    async def _method(self, ctx: Context) -> None:
        embed = await self.get_embed(f"{ctx.command.qualified_name}")
        if embed is not None:
            await ctx.reply(
                embed=embed.set_footer(
                    text=f"Requested by {ctx.author}",
                    icon_url=ctx.author.display_avatar.url,
                ),
            )
            return
        await ctx.reply(f"{ctx.author.mention} something not right? This is not us but the API")

    def command_loader(self) -> None:
        method = self._method
        for end_point in ENDPOINTS:

            @commands.command(name=end_point)
            @commands.cooldown(1, 60, commands.BucketType.user)
            @commands.max_concurrency(1, commands.BucketType.user)
            @commands.is_nsfw()
            @Context.with_type
            async def command_callback(ctx: Context[Parrot]):
                await method(ctx)

            self.bot.add_command(command_callback)

    @commands.command(hidden=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def n(
        self,
        ctx: Context,
        count: int | None = 1,
        *,
        endpoint: Literal["gif", "jav", "rb", "ahegao", "twitter"] = "gif",
    ) -> None:
        """Mature Content. 18+ only Please."""
        em_list: list[discord.Embed] = []

        count = max(1, count or 1)
        count = min(count, 10)

        i: int = 1
        while i <= count:
            r = await self.bot.http_session.get(
                f"https://scathach.redsplit.org/v3/nsfw/{endpoint}/",
                headers=self.bot.GLOBAL_HEADERS,
            )
            if r.status == 200:
                res = await r.json()
                em_list.append(discord.Embed(timestamp=discord.utils.utcnow()).set_image(url=res["url"]))
            i += 1

        ins = PV(em_list)
        await ins.paginate(ctx)

    async def _update_user_age(self, user_id: int, adult: bool) -> None:
        query = {
            "_id": user_id,
        }
        update = {
            "$set": {
                "adult": adult,
            },
        }
        await self.bot.user_collections_ind.update_one(query, update, upsert=True)
        await self.bot.update_user_cache.start(user_id)

    async def check_user_age(self, ctx: Context) -> bool:
        if ctx.author.id in self.bot.owner_ids:
            return True

        if ctx.author.id not in self.bot._user_cache:
            confirm = await ctx.prompt("Are you 18+?")
            if not confirm:
                await self._update_user_age(ctx.author.id, False)
                return False
            await self._update_user_age(ctx.author.id, True)

        return self.bot._user_cache[ctx.author.id].get("adult", False)

    @commands.command(name="18+", aliases=["adult"], hidden=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def adult(self, ctx: Context) -> None:
        """To tell bot that you are 18+. This is required to use NSFW commands. DO NOT FAKE IT.

        If you are caught faking it, you will be blacklisted from using NSFW commands forever."""
        if await self.check_user_age(ctx):
            await ctx.reply("You are already 18+", delete_after=5)
            return
        await self._update_user_age(ctx.author.id, True)
        await ctx.reply("You are now 18+", delete_after=5)

    @commands.command(name="18-", aliases=["notadult"], hidden=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    @Context.with_type
    async def not_adult(self, ctx: Context) -> None:
        """To tell bot that you are not 18+. This is required to use NSFW commands. DO NOT FAKE IT.

        If you are caught faking it, you will be blacklisted from using NSFW commands forever."""
        if not await self.check_user_age(ctx):
            await ctx.reply("You are already not 18+", delete_after=5)
            return
        await self._update_user_age(ctx.author.id, False)
        await ctx.reply("You are now not 18+", delete_after=5)
