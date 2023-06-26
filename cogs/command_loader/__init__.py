# WIP

from __future__ import annotations

import io
from typing import Optional, Union

import discord
from core import Cog, Context, Parrot
from discord.ext import commands
from utilities.config import JEYY_API_TOKEN
from utilities.converters import ToImage

from .endpoints import JEYY_API, JEYY_API_URL

HEADERS = {"Authorization": f"Bearer {JEYY_API_TOKEN}"}


class CommandLoader(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.loader()

    def loader(self) -> None:
        @commands.group(
            name="jeyy",
            aliases=["jeyy.xyz", "j"],
        )
        async def jeyy(ctx: Context) -> None:
            """Get a random image from jeyy.xyz"""
            if ctx.invoked_subcommand is None:
                await self.bot.invoke_help_command(ctx)

        for endpoint in JEYY_API:

            @jeyy.command(name=endpoint)
            async def callback(ctx: Context, *, user: Optional[Union[discord.User, discord.Member]] = None) -> None:
                user = user or ctx.author
                response = await ctx.bot.http_session.get(
                    f"{JEYY_API_URL}/v2/image/{ctx.command.name}",
                    headers=HEADERS,
                    params={"image_url": user.display_avatar.url},
                )
                buf = io.BytesIO(await response.read())
                await ctx.reply(file=discord.File(buf, filename=f"{endpoint}.png"))

        self.bot.add_command(jeyy)

async def setup(bot: Parrot) -> None:
    await bot.add_cog(CommandLoader(bot))
