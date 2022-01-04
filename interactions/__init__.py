from discord.commands import (
    slash_command,
)  # Importing the decorator that makes slash commands.
from discord.ext import commands


class Example(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(
        guild_ids=[741614680652644382]
    )  # Create a slash command for the supplied guilds.
    async def hello(self, ctx):
        await ctx.respond("Hi, this is a slash command from a cog!")


def setup(bot):
    bot.add_cog(Example(bot))

    # https://image.thum.io/get/width/1920/crop/675/noanimate/https://google.com
