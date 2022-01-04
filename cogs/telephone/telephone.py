from __future__ import annotations

from discord.ext import commands
import discord
from time import time

from core import Parrot, Cog, Context
from .method import dial


class Telephone(Cog):
    """To Make calls"""

    def __init__(self, bot: Parrot):
        self.bot = bot
        self.redial = {}
        self.las_call_detail = {}

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{BLACK TELEPHONE}")

    @commands.command(aliases=["call"])
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 180, commands.BucketType.guild)
    @commands.bot_has_permissions(add_reactions=True)
    @Context.with_type
    async def dial(self, ctx: Context, *, server: discord.Guild):
        """
        To dial to other server. Do not misuse this. Else you RIP :|
        """
        if not server:
            await ctx.send(
                "That server no longer exists or bot is being removed from that server"
            )
        self.redial[ctx.guild.id] = server.id
        self.redial[server.id] = ctx.guild.id
        ini = time()
        await dial(self.bot, ctx, server, False)
        fin = time()
        return await ctx.send(
            f"Call Details\n"
            f"`Total Time Taken:` **{round(fin-ini)}**\n"
            f"`Tried to call   :` **{server.name} ({server.id})**\n"
            f"`Called by       :` **{ctx.author.name}#{ctx.author.discriminator}**\n"
            f"`Can Redial?     :` **True**\n"
            f"`Call log saved? :` **False**\n"
        )

    @commands.command(aliases=["recall"])
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 180, commands.BucketType.guild)
    @Context.with_type
    async def redial(self, ctx: Context):
        """To redial the recently called server, if any"""
        try:
            serverid = self.redial[ctx.guild.id]
        except KeyError:
            return await ctx.send("No call logs found")
        else:
            server = self.bot.get_guild(serverid)
            if server:
                ini = time()
                await dial(self.bot, ctx, server, False)
                fin = time()
                return await ctx.send(
                    f"Call Details\n"
                    f"`Total Time Taken:` **{round(fin-ini)}**\n"
                    f"`Tried to call   :` **{server.name} ({server.id})**\n"
                    f"`Called by       :` **{ctx.author.name}#{ctx.author.discriminator}**\n"
                    f"`Can Redial?     :` **True**\n"
                    f"`Call log saved? :` **False**\n"
                )
            await ctx.send(
                "That server no longer exists or bot is being removed from that server"
            )

    @commands.command(aliases=["reversecall"])
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 180, commands.BucketType.guild)
    @Context.with_type
    async def reversedial(self, ctx: Context, *, server: discord.Guild):
        """To make the calls but contents are reverted"""
        if not server:
            await ctx.send(
                "That server no longer exists or bot is being removed from that server"
            )
        self.redial[ctx.guild.id] = server.id
        self.redial[server.id] = ctx.guild.id
        ini = time()
        await dial(self.bot, ctx, server, True)
        fin = time()
        return await ctx.send(
            f"Call Details\n"
            f"`Total Time Taken:` **{round(fin-ini)}**\n"
            f"`Tried to call   :` **{server.name} ({server.id})**\n"
            f"`Called by       :` **{ctx.author.name}#{ctx.author.discriminator}**\n"
            f"`Can Redial?     :` **True**\n"
            f"`Call log saved? :` **False**\n"
        )
