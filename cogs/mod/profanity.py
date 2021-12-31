from __future__ import annotations

from typing import Collection
import typing

from discord.ext import commands, tasks
import discord, random

from utilities.database import parrot_db

from core import Parrot, Cog

with open('extra/duke_nekum.txt') as f:
    quotes = f.read().split('\n')


class Profanity(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db['server_config']
        self.data = {}
        self.update_data.start()

    async def get_bad_words(self, message) -> typing.Optional[list]:
        try:
            return self.data[message.guild.id]
        except KeyError:
            return None
        
    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        if message.author.guild_permissions.administrator:
            return
        bad_words = await self.get_bad_words(message)
        
        if data := await self.collection.find_one({'_id': message.guild.id, 'automod.profanity.enable': {'$exists': True}}):
            try:
                profanity = data['automod']['profanity']['enable']
            except KeyError:
                return
            try:
                ignore = data['automod']['profanity']['channel']
            except KeyError:
                ignore = []
            
            if ignore and (message.channel.id in ignore):
                return
            
            if (not bad_words) and profanity:
                try:
                    bad_words = data['automod']['profanity']['words']
                except KeyError:
                    return

            if not bad_words:
                return

            if any(temp in message.content.lower().split(' ') for temp in bad_words):
                await message.channel.send(f"{message.author.mention} *{random.choice(quotes)}* **[Blacklisted Word] [Warning]**", delete_after=10)

                try:
                    await message.delete()
                except Exception:
                    pass

    @tasks.loop(seconds=5)
    async def update_data(self):
        async for data in self.collection.find({}):
            try:
                bad_words = data['automod']['profanity']['words']
            except KeyError:
                return
            self.data[data['_id']] = bad_words

