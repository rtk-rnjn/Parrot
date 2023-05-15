from __future__ import annotations

from random import choice, random
from typing import Dict, Optional, Set

import discord
from core import Cog, Context, Parrot
from discord.ext import commands

from ._actions import ENDPOINTS


class Actions(Cog):
    """Action commands like hug and kiss"""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.url = "https://api.waifu.pics/sfw"
        self.command_loader()

        self.cached_images: Dict[str, Set[str]] = {}

        self.ON_TESTING = False

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(
            name="Lights_Camera_Action__Emoticon__", id=892434144364220497
        )

    def _try_from_cache(self, ctx: Context) -> Optional[str]:
        return choice(self.cached_images.get(ctx.command.qualified_name, [None]))

    async def send_message(self, ctx: Context, *, url: str = None) -> None:
        if (
            random() > 0.5
            and len(self.cached_images.get(ctx.command.qualified_name, [])) >= 10
        ):
            url = url or choice(self.cached_images[ctx.command.qualified_name])
        else:
            response = await self.bot.http_session.get(
                url or f"{self.url}/{ctx.command.name}"
            )
            if response.status != 200:
                url = self._try_from_cache(ctx)
                if url is None:
                    await ctx.send(
                        f"{ctx.author.mention} Something went wrong, try again later"
                    )
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
        embed.set_footer(
            text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url
        )

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
            async def callback(
                ctx: Context,
            ):
                await method(ctx)

            self.bot.add_command(callback)
