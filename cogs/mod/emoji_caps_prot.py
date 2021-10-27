from __future__ import annotations

from discord.ext import commands, tasks
import discord

from utilities.database import parrot_db

import re, random, typing
from core import Parrot, Cog

with open('extra/duke_nekum.txt') as f:
    quotes = f.read().split('\n')


class EmojiCapsProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.data = {} # TODO: Make cache system
        self.collection = parrot_db['server_config']
    
    async def delete(self, message: discord.Message, *, reason: str=None) -> None:
        try:
            await message.delete(reason=reason)
        except Exception:
            return

    async def get_emoji_count(self, message_content: str) -> int:
        str_count = len(re.findall(r'[\U0001f600-\U0001f650]', message_content))
        dis_count = len(re.findall(r'<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>', message_content))
        return int(str_count + dis_count)
    
    async def get_caps_count(self, message_content: str) -> int:
        caps_count = len(re.findall(r'[A-Z]', message_content))
        return int(caps_count)
    
    async def is_caps_infilterated(self, message: discord.Message) -> typing.Optional[bool]:
        if data_c := await self.collection.find_one({'_id': message.guild.id, 'automod.caps.enable': {'$exists': True}}):
            if not data_c['automod']['caps']['enable']:
                return False
            try:
                ignore = data_c['automod']['caps']['channel']
            except KeyError:
                ignore = []
            if message.channel.id in ignore:
                return False
            try:
                limit = data_c['automod']['caps']['limit']
            except KeyError:
                return False
            if limit == await self.get_caps_count(message.content):
                return True

    async def is_emoji_infilterated(self, message: discord.Message) -> typing.Optional[bool]:
        if data_c := await self.collection.find_one({'_id': message.guild.id, 'automod.emoji.enable': {'$exists': True}}):
            if not data_c['automod']['emoji']['enable']:
                return False
            try:
                ignore = data_c['automod']['emoji']['channel']
            except KeyError:
                ignore = []
            if message.channel.id in ignore:
                return False
            try:
                limit = data_c['automod']['emoji']['limit']
            except KeyError:
                return False
            if limit == await self.get_emoji_count(message.content):
                return True

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        if message.author.guild_permissions.administrator:
            return
        caps_ = await self.is_caps_infilterated(message)
        emoj_ = await self.is_emoji_infilterated(message)
        
        if emoj_ or caps_:
            await self.delete(message, reason='Excess Caps' if caps_ else 'Excess Emoji')
            await message.channel.send(
                f"{message.author.mention} *{random.choice(quotes)}* **[{'Excess Caps' if caps_ else 'Excess Emoji'}] [Warning]**", 
                delete_after=10
            )