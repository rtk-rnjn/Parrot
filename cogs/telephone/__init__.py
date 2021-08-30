from core import Parrot, Cog, Context
from discord.ext import commands
from .method import dial
import discord 

class telephone(Cog):
    """To Make calls"""
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.redial = {}
        self.las_call_detail = {}
    
    @commands.command(aliases=['call'])
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 180, commands.BucketType.guild)
    @commands.bot_has_permissions(add_reactions=True)
    @Context.with_type
    async def dial(self, ctx: Context, *, server: discord.Guild):
        """
        To dial to other server. Do not misuse this. Else you RIP :|
        """
        if not server:
            await ctx.send("That server no longer exists or bot is being removed from that server")
        self.redial[ctx.guild.id] = server.id
        self.redial[server.id] = ctx.guild.id
        await dial(self.bot, ctx, server, False)

    @commands.command(aliases=['recall'])
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
                await dial(self.bot, ctx, server, False)
            else:
                await ctx.send("That server no longer exists or bot is being removed from that server")
    
    @commands.command(aliases=['reversecall'])
    @commands.max_concurrency(1, commands.BucketType.guild)
    @commands.cooldown(1, 180, commands.BucketType.guild)
    @Context.with_type
    async def reversedial(self, ctx: Context, *, server: discord.Guild):
        """To make the calls but contents are reverted"""
        if not server:
            await ctx.send("That server no longer exists or bot is being removed from that server")
        self.redial[ctx.guild.id] = server.id
        self.redial[server.id] = ctx.guild.id
        await dial(self.bot, ctx, server, True)
    
def setup(bot):
    bot.add_cog(telephone(bot))