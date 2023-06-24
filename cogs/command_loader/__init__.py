# WIP

from __future__ import annotations

from typing import Optional

from core import Cog, Context, Parrot
from discord.ext import commands
from utilities.config import JEYY_API_TOKEN
from utilities.converters import ToImage

from .endpoints import JEYY_API, JEYY_API_URL

HEADERS = {"Authorization": f"Bearer {JEYY_API_TOKEN}"}

class CommandLoader(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    def loader(self, **kw) -> None:
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
            async def callback(ctx: Context, *, entity: Optional[ToImage] = None) -> None:
                buf = entity or await ToImage().none(ctx)

                if buf is not None:
                    response = await ctx.bot.http_session.get(
                        f"{JEYY_API_URL}/v2/image/{endpoint}",
                        headers={**HEADERS, **self.bot.GLOBAL_HEADERS},
                        data={"image": buf.read()},  # type: ignore
                    )
                    if response.status == 200:
                        ...
