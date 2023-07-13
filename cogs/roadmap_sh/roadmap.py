from __future__ import annotations

import discord
from core import Cog, Context, Parrot
from discord.ext import commands


class Roadmap(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.group(name="roadmap", invoke_without_command=True)
    async def roadmap(self, ctx: Context) -> None:
        pass

    @roadmap.command(name="pdf")
    async def roadmap_pdf(self, ctx: Context) -> None:
        pass

    @commands.command(name="guides")
    async def roadmap_guides(self, ctx: Context) -> None:
        pass

    @roadmap.command(name="videos")
    async def roadmap_videos(self, ctx: Context) -> None:
        pass

    @roadmap.command(name="links")
    async def roadmap_links(self, ctx: Context) -> None:
        pass

    @roadmap.command(name="best", aliases=["best_practices"])
    async def roadmap_best_practices(self, ctx: Context) -> None:
        pass
