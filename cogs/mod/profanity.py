from __future__ import annotations
from typing import Collection

from discord.ext import commands, tasks
import discord

from utilities.database import parrot_db

from core import Parrot, Cog


class Profanity(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db['server_config']
        self.data = {}

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        
        if data := self.collection.find_one({'_id': message.guild.id, 'automod.profanity.enable': {'$exists': True}}):
            try:
                profanity = data['automod']['profanity']['enable']
            except KeyError:
                return
        
        if profanity:
            try:
                bad_words = data['automod']['profanity']['words']
            except KeyError:
                return
        
        if not bad_words:
            return
        
        