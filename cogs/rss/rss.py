from __future__ import annotations

from core import Parrot, Context, Cog
from discord.ext import commands, tasks
import discord


class RSS(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.group(name="rss", aliases=["rssfeed"])
    @commands.has_permissions(manage_guild=True)
    async def rss(self, ctx: Context) -> None:
        """RSS Feed Management"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @rss.command(name="add")
    async def rss_add(self, ctx: Context, *, link: str) -> None:
        """Add a new RSS Feed"""
        pass

    @rss.command(name="remove")
    async def rss_remove(self, ctx: Context, *, link: str) -> None:
        """Remove an existing RSS Feed"""
        pass

    @rss.command(name="list")
    async def rss_list(self, ctx: Context, *, link: str) -> None:
        """List all RSS Feeds"""
        pass

    @tasks.loop(count=1)
    async def rss_loop(self) -> None:
        pass
