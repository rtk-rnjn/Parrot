from __future__ import annotations

from core import Parrot, Cog

from utilities.database import parrot_db

from discord.ext import commands, tasks
import discord
import random

with open('extra/duke_nekum.txt') as f:
    quotes = f.read().split('\n')


class MentionProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db['server_config']
        self.data = {}
        self.clear_data.start()
    
    async def delete(self, message: discord.Message):
        try:
            await message.delete()
        except Exception:
            return

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        
        if message.author.guild_permissions.administrator:
            return
        
        try:
            data = self.data[message.guild.id]
        except KeyError:
            if data := await self.collection.find_one(
                {
                    '_id': message.guild.id, 
                    'automod.mention.enable': 
                        {'$exists': True}
                }
            ):
                self.data[message.guild.id] = data
            else:
                return

        if self.data[message.guild.id]['automod']['mention']['enable']:
            try:
                ignore = self.data[message.guild.id]['automod']['mention']['channel']
            except KeyError:
                ignore = []
            
            if message.channel.id in ignore:
                return
            
            try:
                count = self.data[message.guild.id]['automod']['mention']['count']
            except KeyError:
                count = None
            
            if not count: return
            
            if len(message.mentions) >= count:
                await self.delete(message)
                await message.channel.send(
                    f"{message.author.mention} *{random.choice(quotes)}* **[Mass Mention] [Warning]**", 
                    delete_after=10
                )
    
    @tasks.loop(seconds=900)
    async def clear_data(self):
        self.data = {}
        
