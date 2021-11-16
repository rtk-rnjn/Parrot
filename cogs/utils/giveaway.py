from __future__ import annotations

from core import Parrot, Cog, Context
import discord
from discord.ext import commands


class Giveaway(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        
    @commands.group(name='giveaway')
    @commands.bot_has_permissions(embed_link=True, add_reactions=True)
    @commands.has_permissions(manage_guild=True, add_reactions=True)
    async def giveaway(self, ctx: Context):
        """To make giveaways in the server"""
        pass
    
    @giveaway.command()
    async def create(self, ctx: Context):
        """To create a giveaway in the server"""
        pass
    
    @giveaway.command()
    async def end(self, ctx: Context):
        """To end the giveaway"""
        pass
    
    @giveaway.command()
    async def reroll(self, ctx: Context):
        """To reroll the giveaway winners"""
        pass
    