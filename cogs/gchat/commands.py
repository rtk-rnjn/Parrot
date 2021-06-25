from discord.ext import commands
import discord, json, aiohttp
from discord import Webhook, AsyncWebhookAdapter

class commands(commands.Cog, name="Global Chat"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    


def setup(bot):
    bot.add_cog(commands(bot))