from __future__ import annotations

import typing

from discord.ext import commands, tasks
import discord, random

from utilities.database import parrot_db
from utilities.regex import LINKS_NO_PROTOCOLS, LINKS_RE

from core import Parrot, Cog

with open('extra/duke_nekum.txt') as f:
    quotes = f.read().split('\n')


class LinkProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db['server_config']
        self.data = {}
        self.update_data.start()

    async def has_links(self, message_content: str) -> bool:
        url1 = LINKS_NO_PROTOCOLS.search(message_content)
        url2 = LINKS_RE.search(message_content)
        url = url1 or url2
        if url:
            return True
        else:
            return False
        
    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        if message.author.guild_permissions.administrator:
            return
        if data := await self.collection.find_one({'_id': message.guild.id, 'automod.antilinks.enable': {'$exists': True}}):
            prot = data['automod']['antilinks']['enable']
            
            if not prot:
                return
            
            try:
                whitelist = data['automod']['antilinks']['whitelist']
            except KeyError:
                pass
            
            try:
                ignore = data['automod']['antilinks']['channel']
            except KeyError:
                pass
            
            if message.channel.id in ignore:
                return
            
            if any(temp in message.content for temp in whitelist):
                return

            has_links = await self.has_links(message.content)
            
            if has_links:
                await message.channel.send(f"{message.author.mention} *{random.choice(quotes)}* **[Links Protection] [Warning]**", delete_after=10)
                try:
                    await message.delete()
                except Exception:
                    pass
    
    @tasks.loop(hours=0.5)
    async def update_data(self):
        pass