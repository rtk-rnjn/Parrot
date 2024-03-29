from __future__ import annotations

from time import time

import discord
from core import Cog, Context, Parrot
from discord.ext import commands

from .method import dial


class Telephone(Cog):
    """To Make calls over other server."""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self.redial = {}
        self.las_call_detail = {}
        self.ON_TESTING = False

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{BLACK TELEPHONE}")

    @commands.command(aliases=["call"])
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 180, commands.BucketType.guild)
    @commands.bot_has_permissions(add_reactions=True)
    async def dial(self, ctx: Context, *, server: discord.Guild):
        """To dial to other server. Do not misuse this."""
        if not server:
            await ctx.send("That server no longer exists or bot is being removed from that server")
        self.redial[ctx.guild.id] = server.id
        self.redial[server.id] = ctx.guild.id
        ini = time()
        await dial(self.bot, ctx, server, False)
        fin = time()
        return await ctx.send(
            f"Call Details\n"
            f"`Total Time Taken:` **{round(fin-ini)}**\n"
            f"`Tried to call   :` **{server.name} ({server.id})**\n"
            f"`Called by       :` **{ctx.author}**\n"
            f"`Can Redial?     :` **True**\n"
            f"`Call log saved? :` **False**\n",
        )

    @commands.command(name="redial", aliases=["recall"])
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 180, commands.BucketType.guild)
    async def redial_call(self, ctx: Context):
        """To redial the recently called server, if any."""
        try:
            serverid = self.redial[ctx.guild.id]
        except KeyError:
            return await ctx.send("No call logs found")
        else:
            if server := self.bot.get_guild(serverid):
                ini = time()
                await dial(self.bot, ctx, server, False)
                fin = time()
                return await ctx.send(
                    f"Call Details\n"
                    f"`Total Time Taken:` **{round(fin-ini)}**\n"
                    f"`Tried to call   :` **{server.name} ({server.id})**\n"
                    f"`Called by       :` **{ctx.author}**\n"
                    f"`Can Redial?     :` **True**\n"
                    f"`Call log saved? :` **False**\n",
                )
            await ctx.send("That server no longer exists or bot is being removed from that server")

    @commands.command(aliases=["reversecall"])
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 180, commands.BucketType.guild)
    async def reversedial(self, ctx: Context, *, server: discord.Guild):
        """To make the calls but contents are reverted."""
        if not server:
            await ctx.send("That server no longer exists or bot is being removed from that server")
        self.redial[ctx.guild.id] = server.id
        self.redial[server.id] = ctx.guild.id
        ini = time()
        await dial(self.bot, ctx, server, True)
        fin = time()
        return await ctx.send(
            f"Call Details\n"
            f"`Total Time Taken:` **{round(fin-ini)}**\n"
            f"`Tried to call   :` **{server.name} ({server.id})**\n"
            f"`Called by       :` **{ctx.author}**\n"
            f"`Can Redial?     :` **True**\n"
            f"`Call log saved? :` **False**\n",
        )
