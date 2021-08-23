from discord.ext import commands
import discord

from core import Parrot, Context, Cog

from cogs.ticket import method as mt


class ticket(Cog):
    """A simple ticket service, trust me it's better than YAG. LOL!"""
    def __init__(self, bot: Parrot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.member)
    @commands.bot_has_permissions(manage_channels=True,
                                  embed_links=True,
                                  manage_roles=True)
    async def new(self, ctx: Context, *, args=None):
        """
			This creates a new ticket. Add any words after the command if you'd like to send a message when we initially create your ticket.
			"""
        await self.bot.wait_until_ready()
        await mt._new(ctx, args)

    @commands.command()
    @commands.bot_has_permissions(manage_channels=True, embed_links=True)
    async def close(self, ctx):
        """
			Use this to close a ticket. This command only works in ticket channels.
			"""
        await self.bot.wait_until_ready()
        await mt._close(ctx, self.bot)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.bot_has_permissions(embed_links=True)
    async def save(self, ctx):
        """
			Use this to save the transcript of a ticket. This command only works in ticket channels.
			"""
        await self.bot.wait_until_ready()
        await mt._save(ctx, self.bot)




def setup(bot):
    bot.add_cog(ticket(bot))
