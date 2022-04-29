from __future__ import annotations

from core import Parrot, Cog, Context
from discord.ext import commands
import discord


class Hidden(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @commands.group(hidden=True, invoke_without_command=True)
    async def optout(self, ctx: Context):
        """Opt-out to the certain configuration"""
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)

    @optout.command(name="gitlink", hidden=True)
    async def optout_gitlink(self, ctx: Context):
        """Opt-out for gitlink to codeblock"""
        await self.bot.mongo.extra.misc.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"gitlink": ctx.author.id}},
            upsert=True,
        )
        await ctx.send(
            f"{ctx.author.mention} You have opted-out to the use of gitlink in codeblocks."
        )

    @optout.command(name="global", hidden=True)
    async def optout_global(self, ctx: Context):
        """Opt-out for global chat"""
        await self.bot.mongo.extra.misc.update_one(
            {"_id": ctx.guild.id}, {"$addToSet": {"global": ctx.author.id}}, upsert=True
        )
        await ctx.send(
            f"{ctx.author.mention} You have opted-out to the use of global chat."
        )

    @optout.command(name="command", aliases=["commands", "cmd"], hidden=True)
    async def optout_command(self, ctx: Context):
        """Opt-out for command usage"""
        await self.bot.mongo.extra.misc.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"command": ctx.author.id}},
            upsert=True,
        )
        await ctx.send(
            f"{ctx.author.mention} You have opted-out to the use of Parrot commands."
        )

    @commands.group(hidden=True, invoke_without_command=True)
    async def optin(self, ctx: Context):
        """Opt-in to the certain configuration"""
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)

    @optin.command(name="gitlink", hidden=True)
    async def optin_gitlink(self, ctx: Context):
        """Opt-in for gitlink to codeblock"""
        await self.bot.mongo.extra.misc.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"gitlink": ctx.author.id}}, upsert=True
        )
        await ctx.send(
            f"{ctx.author.mention} You have opted-in to the use of gitlink in codeblocks."
        )

    @optin.command(name="global", hidden=True)
    async def optin_global(self, ctx: Context):
        """Opt-in for global chat"""
        await self.bot.mongo.extra.misc.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"global": ctx.author.id}}, upsert=True
        )
        await ctx.send(
            f"{ctx.author.mention} You have opted-in to the use of global chat."
        )

    @optin.command(name="command", aliases=["commands", "cmd"], hidden=True)
    async def optin_command(self, ctx: Context):
        """Opt-in for command usage"""
        await self.bot.mongo.extra.misc.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"command": ctx.author.id}}, upsert=True
        )
        await ctx.send(
            f"{ctx.author.mention} You have opted-in to the use of Parrot commands."
        )
