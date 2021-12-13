

from discord.ext import commands
from core import Parrot, Cog


class Example(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

    @commands.slash_command(guild_ids=[741614680652644382])  # Create a slash command for the supplied guilds.
    async def hello(self, ctx):
        await ctx.respond("Hi, this is a slash command from a cog!")


def setup(bot):
    bot.add_cog(Example(bot))