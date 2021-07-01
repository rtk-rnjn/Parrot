import discord, traceback, sys, math, random
from discord.ext import commands
from datetime import datetime
from utils.exceptions import NukeBotError
from core.cog import Cog

from utils import database

with open("storing/quote.txt") as f:
    quote = f.read()

quote = quote.split('\n')


class CommandErrorHandler(Cog):
    """This category is of no use for you, ignore it."""
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_command_completion(self, ctx):
        """This event will be triggered when the command is being completed; triggered by [discord.User]!"""
        if ctx.author.bot: return
        await database.cmd_usage_dtd(str(ctx.command.name),
                                     str(datetime.utcnow()), int(ctx.guild.id),
                                     int(ctx.message.author.id), 1)

    @Cog.listener()
    async def on_command(self, ctx):
        """This event will be triggered when the command is being called; triggered by [discord.User]!"""
        if ctx.author.bot: return
        await database.cmd_usage_dtd(str(ctx.command.name),
                                     str(datetime.utcnow()), int(ctx.guild.id),
                                     int(ctx.message.author.id), 0)


def setup(bot):
    bot.add_cog(CommandErrorHandler(bot))
