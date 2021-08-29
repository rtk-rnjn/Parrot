from core import Parrot, Cog, Context
from discord.ext import commands
from .method import dial

class telephone(Cog):
    """To Make calls"""
    def def __init__(self, bot: Parrot):
        self.bot = bot
        self.redial = {}
        self.las_call_detail = {}
    
    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 180, commands.BucketType.guild)
    @Context.with_type
    async def dial(self, ctx: Context, *, server: discord.Guild):
        """
        To dial to other server. Do not misuse this. Else you RIP :|
        """
        if not server:
            await ctx.send("That server don't exists or bot is being removed from that serer")
        self.redial[ctx.guild.id] = server.id
        self.redial[server.id] = ctx.guild.id
        await dial(self.bot, ctx, server, False)

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 180, commands.BucketType.guild)
    @Context.with_type
    async def redial(self, ctx: Context):
        pass