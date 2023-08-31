from __future__ import annotations

from random import choice, random

import discord
from core import Cog, Context, Parrot
from discord.ext import commands

from ._actions import ENDPOINTS

HALF = 0.5
MAX_IMAGES = 10
HTTP_RESPONSE = 200


class Actions(Cog):
    """Action commands like hug and kiss."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.url = "https://api.waifu.pics/sfw"

        self.cached_images: dict[str, set[str]] = {}

        self.ON_TESTING = False

    async def cog_load(self):
        self.command_loader()

    async def cog_unload(self):
        for end_point in ENDPOINTS:
            self.bot.remove_command(end_point)

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="Lights_Camera_Action__Emoticon__", id=892434144364220497)

    def _try_from_cache(self, ctx: Context) -> str | None:
        return choice(self.cached_images.get(ctx.command.qualified_name, [None]))

    async def send_message(self, ctx: Context, *, url: str = None) -> None:
        if random() > HALF and len(self.cached_images.get(ctx.command.qualified_name, [])) >= MAX_IMAGES:
            url = url or choice(self.cached_images[ctx.command.qualified_name])
        else:
            response = await self.bot.http_session.get(url or f"{self.url}/{ctx.command.name}")
            if response.status != HTTP_RESPONSE:
                url = self._try_from_cache(ctx)
                if url is None:
                    await ctx.send(f"{ctx.author.mention} Something went wrong, try again later")
                    return
            else:
                data = await response.json()
                url = data["url"]

        embed = discord.Embed(
            title=f"{ctx.command.name.title()}",
            color=self.bot.color,
            timestamp=ctx.message.created_at,
        )

        embed.set_image(url=url)

        if ctx.command.qualified_name not in self.cached_images:
            self.cached_images[ctx.command.qualified_name] = set()

        self.cached_images[ctx.command.qualified_name].add(url)

        await ctx.reply(embed=embed)

    def command_loader(self) -> None:
        method = self.send_message
        for end_point in ENDPOINTS:

            @commands.command(name=end_point)
            @commands.cooldown(1, 8, commands.BucketType.member)
            @Context.with_type
            async def callback(ctx: Context):
                await method(ctx)

            self.bot.add_command(callback)
