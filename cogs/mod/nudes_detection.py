from __future__ import annotations

from discord.ext import commands, tasks
import discord

from utilities.database import parrot_db
import aiohttp, asyncio, typing, os

with open('extra/duke_nekum.txt') as f:
    quotes = f.read().split('\n')

import random 

from core import Parrot, Cog

class NudeDetection(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.data = {}
        self.collection = parrot_db['server_config']
        self.update_data.start()
        self.endpoint = "https://api.deepai.org/api/nsfw-detector"
        self.key = os.environ['DEEP_AI']

    async def contains_nsfw(self, link: str) -> bool:
        async with aiohttp.ClientSession() as session:
            data = await session.post(self.endpoint, data={'image': link}, headers={'api-key': self.key})
            json = await data.json()
            if json['nsfw_score'] > 65:
                return True
            else:
                return False

    async def delete(self, message):
        try:
            await message.delete()
        except Exception:
            pass
    
    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        
        if message.author.guild_permissions.administrator:
            return # we love admin, don't we?
        
        if message.channel.is_nsfw():
            return
        
        try:
            self.data[message.guild.id]
        except Exception:
            return
        
        if not self.data[message.guild.id]:
            return
        
        if message.channel.id in self.data[message.guild.id]['channel']:
            return
            
        if message.content.endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
            is_nude = await self.contains_nsfw(message.content)
        
        if is_nude:
            await self.delete(message)
            await message.channel.send(f"{message.author.mention} *{random.choice(quotes)}* **[Blacklisted Word] [Warning]**", delete_after=10)
            return
        
        if message.attachments:
            for file in message.attachments:
                if file.url.endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                    is_nude = await self.contains_nsfw(file.url)
                
                if is_nude:
                    await self.delete(message)
                    await message.channel.send(f"{message.author.mention} *{random.choice(quotes)}* **[Blacklisted Word] [Warning]**", delete_after=10)
                    return
    
    @tasks.loop(seconds=5)
    async def update_data(self):
        async for data in self.collection.find({'automod.nudedetection.enable': {'$exists': True}}):
            if data['automod']['nudedetection']['enable']:
                try:
                    self.data[data['_id']] = data['automod']['nudedetection']['channel']
                except KeyError:
                    self.data[data['_id']] = []