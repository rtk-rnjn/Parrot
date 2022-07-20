from __future__ import annotations

import hashlib

import discord
from core import Cog, Context, Parrot
from discord.ext import commands


class Hidden(Cog):
    """This category is for you. You can opt-in or opt-out certain feature of the bot"""
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{KEY}")

    @commands.group(invoke_without_command=True)
    async def optout(self, ctx: Context):
        """Opt-out to the certain configuration"""
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)

    @optout.command(name="gitlink")
    async def optout_gitlink(self, ctx: Context):
        """Opt-out for gitlink to codeblock."""
        await self.bot.mongo.extra.misc.update_one(
            {"_id": ctx.guild.id},
            {"$pull": {"gitlink": ctx.author.id}},
            upsert=True,
        )
        await ctx.send(
            f"{ctx.author.mention} You have opted-out to the use of gitlink in codeblocks."
        )

    @optout.command(name="global")
    async def optout_global(self, ctx: Context):
        """Opt-out for global chat"""
        await self.bot.mongo.extra.misc.update_one(
            {"_id": ctx.guild.id}, {"$addToSet": {"global": ctx.author.id}}, upsert=True
        )
        await ctx.send(
            f"{ctx.author.mention} You have opted-out to the use of global chat."
        )

    @optout.command(name="command", aliases=["commands", "cmd"])
    async def optout_command(self, ctx: Context):
        """Opt-out for command usage.
        Beware after opting-out, you will not be able to use commands anymore.
        It is similar to self banning from using the bot"""
        await self.bot.mongo.extra.misc.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"command": ctx.author.id}},
            upsert=True,
        )
        await ctx.send(
            f"{ctx.author.mention} You have opted-out to the use of Parrot commands."
        )

    @optout.command(name="equation")
    async def optout_equation(self, ctx: Context):
        """Opt-out for equation usage"""
        await self.bot.mongo.extra.misc.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"equation": ctx.author.id}},
            upsert=True,
        )
        await ctx.send(
            f"{ctx.author.mention} You have opted-out to the use of equations."
        )

    @commands.group(invoke_without_command=True)
    async def optin(self, ctx: Context):
        """Opt-in to the certain configuration"""
        if ctx.invoked_subcommand is None:
            await self.bot.invoke_help_command(ctx)

    @optin.command(name="gitlink")
    async def optin_gitlink(self, ctx: Context):
        """Opt-in for gitlink to codeblock"""
        await self.bot.mongo.extra.misc.update_one(
            {"_id": ctx.guild.id},
            {"$addToSet": {"gitlink": ctx.author.id}},
            upsert=True,
        )
        await ctx.send(
            f"{ctx.author.mention} You have opted-in to the use of gitlink in codeblocks."
        )

    @optin.command(name="global")
    async def optin_global(self, ctx: Context):
        """Opt-in for global chat"""
        await self.bot.mongo.extra.misc.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"global": ctx.author.id}}, upsert=True
        )
        await ctx.send(
            f"{ctx.author.mention} You have opted-in to the use of global chat."
        )

    @optin.command(name="command", aliases=["commands", "cmd"])
    async def optin_command(self, ctx: Context):
        """Opt-in for command usage"""
        await self.bot.mongo.extra.misc.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"command": ctx.author.id}}, upsert=True
        )
        await ctx.send(
            f"{ctx.author.mention} You have opted-in to the use of Parrot commands."
        )

    @optin.command(name="equation")
    async def optin_equation(self, ctx: Context):
        """Opt-in for equation usage"""
        await self.bot.mongo.extra.misc.update_one(
            {"_id": ctx.guild.id}, {"$pull": {"equation": ctx.author.id}}, upsert=True
        )
        await ctx.send(
            f"{ctx.author.mention} You have opted-in to the use of equations."
        )

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def activate(self, ctx: Context, code: str):
        """To upgrade the server to premium"""

        code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
        if data := await self.bot.mongo.extra.subscription.find_one(
            {"hash": code_hash}
        ):
            if data.get("uses", 0) > data.get("limit", 0):
                await ctx.send(
                    f"{ctx.author.mention} This code has been used up. Please ask for new code in support server"
                )
                return

            if data.get("guild", None) is not None and data["guild"] != ctx.guild.id:
                await ctx.send(
                    f"{ctx.author.mention} This code is not for this server. Please ask for new code in support server"
                )
                return

            if data.get("expiry", None) is not None and data["expiry"] < int(
                discord.utils.utcnow().timestamp()
            ):
                await ctx.send(
                    f"{ctx.author.mention} This code has expired. Please ask for new code in support server"
                )
                return

            res = await ctx.prompt(
                f"{ctx.author.mention} are you sure you want to upgrade to premium?"
            )
            if not res:
                return await ctx.send(f"{ctx.author.mention} cancelled.")
            await self.bot.mongo.extra.subscription.update_one(
                {"hash": code_hash}, {"$inc": {"uses": 1}}, upsert=True
            )
            await self.bot.mongo.parrot_db.server_config.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"premium": True}},
                upsert=True,
            )
            await ctx.send(f"{ctx.author.mention} upgraded to premium :tada:")
        else:
            await ctx.send(
                f"{ctx.author.mention} This code is invalid. Please ask for new code in support server"
            )

    @Cog.listener()
    async def on_command_completion(self, ctx: Context):
        """
        This is called when a command is completed.
        """
        if ctx.cog is None:
            return

        if ctx.command.cog.qualified_name.lower() == "hidden":
            await self.bot.update_opt_in_out.start()
