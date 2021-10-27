from __future__ import annotations

from core import Parrot, Cog

from discord.ext import commands
import discord, random

from utilities.database import parrot_db

with open('extra/duke_nekum.txt') as f:
    quotes = f.read().split('\n')


class SpamProt(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.collection = parrot_db['server_config']
        self.cd_mapping = commands.CooldownMapping.from_cooldown(
            5, 5, commands.BucketType.Member)
        
    async def delete(self, message: discord.Message, *, reason: str=None) -> None:
        def check(m: discord.Message):
            return m.author.id == message.author.id
        try:
            await message.channel.purge(5, check=check, reason=reason)
        except Exception:
            pass
    
    @Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or (not message.guild):
            return
        if message.author.guild_permissions.administrator:
            return
        bucket = self.cd_mapping.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            if data := await self.collection.find_one({'_id': message.guild.id, 'automod.spam.enable': {'$exists': True}}):
                if not data['automod']['spam']['enable']:
                    return
                try:
                    ignore = data['automod']['spam']['channel']
                except KeyError:
                    ignore = []
                if message.channel.id in ignore:
                    return
                await self.delete(message)
                await message.channel.send(f"{message.author.mention} *{random.choice(quotes)}* **[Spam Protection] [Warning]**", delete_after=10)